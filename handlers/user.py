"""
Xodimlar uchun handlerlar - Vazifalar, Profil, Natijalar
"""
import pytz
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from database import db
from keyboards.user_kb import (
    get_user_menu, get_tasks_keyboard, get_task_detail_keyboard,
    get_profile_keyboard, get_profile_edit_keyboard,
    get_branches_keyboard, get_shift_keyboard, get_cancel_keyboard,
    get_branch_select_keyboard, get_shift_select_keyboard,
    get_cancel_inline_keyboard
)
from config import SHIFTS, RESULT_TYPES, ADMIN_IDS
from utils import helpers

from aiogram.exceptions import TelegramBadRequest # Xatolarni tutish uchun

from config import TIMEZONE # Config faylingizda 'Asia/Tashkent' borligini ko'rdik

router = Router()


# ============= FSM States =============

class TaskSubmission(StatesGroup):
    waiting_text = State()
    waiting_photo = State()


class ProfileEdit(StatesGroup):
    editing_name = State()
    editing_branch = State()
    editing_shift = State()


# ============= VAZIFALARIM =============

@router.message(F.text == "📋 Vazifalarim")
async def show_my_tasks(message: Message):
    """Vazifalar ro'yxatini ko'rsatish"""
    user_id = message.from_user.id

    # Admin bo'lsa, admin panelni ko'rsatish
    if user_id in ADMIN_IDS:
        await message.answer("Siz adminsiz. /admin buyrug'ini ishlating.")
        return

    # Xodim tekshiruvi
    employee = await db.get_employee_by_telegram_id(user_id)
    if not employee:
        await message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz!\n"
            "/start buyrug'ini yuboring.",
            parse_mode="HTML"
        )
        return

    # Vazifalarni olish
    tasks = await db.get_employee_tasks_by_telegram_id(user_id)

    if not tasks:
        await message.answer(
            "📭 <b>Sizga hozircha vazifalar yo'q</b>\n\n"
            "Yangi vazifalar paydo bo'lganda sizga xabar beramiz!",
            parse_mode="HTML"
        )
        return

    text = f"📋 <b>Sizning vazifalaringiz</b>\n\n"
    text += f"Jami: {len(tasks)} ta vazifa\n\n"
    text += "Batafsil ko'rish uchun tanlang:"

    await message.answer(text, reply_markup=get_tasks_keyboard(tasks), parse_mode="HTML")


@router.callback_query(F.data == "my_tasks")
async def callback_my_tasks(callback: CallbackQuery):
    """Vazifalar ro'yxatiga qaytish"""
    user_id = callback.from_user.id
    tasks = await db.get_employee_tasks_by_telegram_id(user_id)

    if not tasks:
        await callback.message.edit_text(
            "📭 <b>Sizga hozircha vazifalar yo'q</b>\n\n"
            "Yangi vazifalar paydo bo'lganda sizga xabar beramiz!",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"📋 <b>Sizning vazifalaringiz</b>\n\n"
    text += f"Jami: {len(tasks)} ta vazifa\n\n"
    text += "Batafsil ko'rish uchun tanlang:"

    await callback.message.edit_text(text, reply_markup=get_tasks_keyboard(tasks), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "tasks_refresh")
async def callback_tasks_refresh(callback: CallbackQuery):
    """Vazifalaringizni yangilash (Xatolarsiz variant)"""
    user_id = callback.from_user.id
    tasks = await db.get_employee_tasks_by_telegram_id(user_id)

    # 1. Vazifalar yo'q bo'lsa
    if not tasks:
        new_text = (
            "📭 <b>Sizga hozircha vazifalar yo'q</b>\n\n"
            "Yangi vazifalar paydo bo'lganda sizga xabar beramiz!"
        )
        try:
            await callback.message.edit_text(new_text, parse_mode="HTML")
        except TelegramBadRequest:
            # Agar xabar matni allaqachon shunday bo'lsa, e'tiborsiz qoldiramiz
            pass

        await callback.answer("🔄 Yangilandi!")
        return

    # 2. Vazifalar bor bo'lsa
    text = f"📋 <b>Sizning vazifalaringiz</b>\n\n"
    text += f"Jami: {len(tasks)} ta vazifa\n\n"
    text += "Batafsil ko'rish uchun tanlang:"

    keyboard = get_tasks_keyboard(tasks)

    try:
        # Xabarni tahrirlash
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest as e:
        # Agar "message is not modified" xatosi bo'lsa, bot to'xtab qolmaydi
        if "message is not modified" in str(e):
            await callback.answer("🔄 Ma'lumotlar o'zgarmagan.")
            return
        else:
            # Boshqa turdagi BadRequest xatolari bo'lsa, ularni ko'rsatish
            raise e

    await callback.answer("🔄 Yangilandi!")


@router.callback_query(F.data.startswith("task_view_"))
async def callback_task_view(callback: CallbackQuery):
    """Vazifa tafsilotlarini ko'rsatish"""
    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    user_id = callback.from_user.id

    # Allaqachon natija yuborgan yoki yo'qligini tekshirish
    already_submitted = await db.has_submitted_result(task_id, user_id)

    # Deadline o'tgan yoki yo'qligini tekshirish
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    deadline_str = task['deadline']

    try:
        deadline = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
            try:
                # Vaqtni o'qiymiz
                deadline = datetime.strptime(deadline_str, fmt)
                # UNGA VAQT MINTOQASINI BIRIKTIRAMIZ (localize)
                deadline = tz.localize(deadline)
                break
            except ValueError:
                continue

        if deadline is None:
            deadline = datetime.fromisoformat(deadline_str)
            # Agar ISO formatdan kelsa va mintaqasi bo'lmasa, biriktiramiz
            if deadline.tzinfo is None:
                deadline = tz.localize(deadline)

    except Exception:
        deadline = now

    # Endi solishtirish 100% ishlaydi
    is_expired = now > deadline

    text = f"📋 <b>{task['title']}</b>\n\n"
    text += f"📝 {task['description']}\n\n"
    text += f"🕐 Boshlanish: {helpers.format_datetime(task['start_time'])}\n"
    text += f"⏰ Deadline: {helpers.format_datetime(task['deadline'])}\n"
    res_type = RESULT_TYPES.get(task['result_type'], "Noma'lum")
    text += f"📊 Natija turi: {res_type}\n\n"

    if already_submitted:
        text += "✅ <b>Siz bu vazifani allaqachon bajargansiz!</b>"
        is_completed = True
    elif is_expired:
        text += f"⏰ <b>Vazifa muddati tugagan!</b>\n"
        text += f"Kechikkan natijalar ham qabul qilinadi."
        is_completed = False
    else:
        remaining = helpers.time_until(deadline)
        text += f"⏳ Qolgan vaqt: {remaining}"
        is_completed = False

    await callback.message.edit_text(
        text,
        reply_markup=get_task_detail_keyboard(task_id, task['result_type'], is_completed),
        parse_mode="HTML"
    )
    await callback.answer()


# ============= NATIJA YUBORISH =============

@router.callback_query(F.data.startswith("submit_text_"))
async def callback_submit_text(callback: CallbackQuery, state: FSMContext):
    """Matn natijasini yuborish jarayonini boshlash"""
    task_id = int(callback.data.split("_")[2])

    # Tekshirish
    already_submitted = await db.has_submitted_result(task_id, callback.from_user.id)
    if already_submitted:
        await callback.answer("❌ Siz bu vazifani allaqachon bajargansiz!", show_alert=True)
        return

    await state.update_data(task_id=task_id)
    await callback.message.answer(
        "📝 <b>Natija yuborish</b>\n\n"
        "Iltimos, natijangizni matn ko'rinishida yuboring:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TaskSubmission.waiting_text)
    await callback.answer()


@router.message(TaskSubmission.waiting_text)
async def process_text_result(message: Message, state: FSMContext, bot: Bot):
    """Matn natijasini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_menu())
        return

    data = await state.get_data()
    task_id = data.get('task_id')

    if not task_id:
        await state.clear()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=get_user_menu())
        return

    try:
        # Natijani yuborish
        result_id, position = await db.submit_task_result_by_telegram_id(
            task_id=task_id,
            telegram_id=message.from_user.id,
            result_text=message.text
        )

        if result_id == 0:
            await message.answer(
                "❌ Xatolik! Siz ro'yxatdan o'tmagansiz.",
                reply_markup=get_user_menu()
            )
            await state.clear()
            return

        # Deadline tekshiruvi
        task = await db.get_task(task_id)
        is_late = False

        if task:
            try:
                deadline_str = task['deadline']
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    deadline = datetime.fromisoformat(deadline_str)

                if datetime.now() > deadline:
                    is_late = True
            except Exception:
                pass

        # Xodimga javob
        position_emoji = helpers.get_position_emoji(position)

        if is_late:
            await message.answer(
                f"⏰ <b>Natija qabul qilindi (Kechiktirilgan)</b>\n\n"
                f"{position_emoji} Siz ushbu vazifani {position}-bo'lib bajardingiz!\n\n"
                f"⚠️ Afsuski, deadline o'tgan edi.",
                reply_markup=get_user_menu(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"✅ <b>Natija qabul qilindi!</b>\n\n"
                f"{position_emoji} Tabriklaymiz! Siz ushbu vazifani {position}-bo'lib bajardingiz!",
                reply_markup=get_user_menu(),
                parse_mode="HTML"
            )

        # Adminga xabar yuborish
        employee = await db.get_employee_by_telegram_id(message.from_user.id)
        if employee and task:
            for admin_id in ADMIN_IDS:
                try:
                    late_text = " (⚠️ Kechiktirilgan)" if is_late else ""
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"📬 <b>Yangi natija!</b>{late_text}\n\n"
                             f"📋 Vazifa: {task['title']}\n"
                             f"👤 Xodim: {employee['first_name']} {employee['last_name']}\n"
                             f"🏢 Filial: {employee['branch_name']}\n"
                             f"📝 Natija turi: Matn\n\n"
                             f"💬 Natija:\n{message.text[:500]}",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\nIltimos, qaytadan urinib ko'ring.",
            reply_markup=get_user_menu()
        )

    await state.clear()


@router.callback_query(F.data.startswith("submit_photo_"))
async def callback_submit_photo(callback: CallbackQuery, state: FSMContext):
    """Rasm natijasini yuborish jarayonini boshlash"""
    task_id = int(callback.data.split("_")[2])

    # Tekshirish
    already_submitted = await db.has_submitted_result(task_id, callback.from_user.id)
    if already_submitted:
        await callback.answer("❌ Siz bu vazifani allaqachon bajargansiz!", show_alert=True)
        return

    await state.update_data(task_id=task_id)
    await callback.message.answer(
        "📸 <b>Natija yuborish</b>\n\n"
        "Iltimos, natijangizni rasm ko'rinishida yuboring:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TaskSubmission.waiting_photo)
    await callback.answer()


@router.message(TaskSubmission.waiting_photo, F.photo)
async def process_photo_result(message: Message, state: FSMContext, bot: Bot):
    """Rasm natijasini qabul qilish"""
    data = await state.get_data()
    task_id = data.get('task_id')

    if not task_id:
        await state.clear()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=get_user_menu())
        return

    photo = message.photo[-1]  # Eng katta rasmni olish
    photo_file_id = photo.file_id
    photo_unique_id = photo.file_unique_id

    # Unique ID tekshiruvi
    if await db.check_photo_used(photo_unique_id):
        await message.answer(
            "❌ <b>Bu rasm avval ishlatilgan!</b>\n\n"
            "Iltimos, yangi rasm yuboring.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        # Natijani yuborish
        result_id, position = await db.submit_task_result_by_telegram_id(
            task_id=task_id,
            telegram_id=message.from_user.id,
            result_photo_id=photo_file_id,
            file_unique_id=photo_unique_id
        )

        if result_id == 0:
            await message.answer(
                "❌ Xatolik! Siz ro'yxatdan o'tmagansiz.",
                reply_markup=get_user_menu()
            )
            await state.clear()
            return

        # Deadline tekshiruvi
        task = await db.get_task(task_id)
        is_late = False

        if task:
            try:
                deadline_str = task['deadline']
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    deadline = datetime.fromisoformat(deadline_str)

                if datetime.now() > deadline:
                    is_late = True
            except Exception:
                pass

        position_emoji = helpers.get_position_emoji(position)

        if is_late:
            await message.answer(
                f"⏰ <b>Natija qabul qilindi (Kechiktirilgan)</b>\n\n"
                f"{position_emoji} Siz ushbu vazifani {position}-bo'lib bajardingiz!\n\n"
                f"⚠️ Afsuski, deadline o'tgan edi.",
                reply_markup=get_user_menu(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"✅ <b>Natija qabul qilindi!</b>\n\n"
                f"{position_emoji} Tabriklaymiz! Siz ushbu vazifani {position}-bo'lib bajardingiz!",
                reply_markup=get_user_menu(),
                parse_mode="HTML"
            )

        # Adminga rasm bilan xabar yuborish
        employee = await db.get_employee_by_telegram_id(message.from_user.id)
        if employee and task:
            for admin_id in ADMIN_IDS:
                try:
                    late_text = " (⚠️ Kechiktirilgan)" if is_late else ""
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=f"📬 <b>Yangi natija!</b>{late_text}\n\n"
                                f"📋 Vazifa: {task['title']}\n"
                                f"👤 Xodim: {employee['first_name']} {employee['last_name']}\n"
                                f"🏢 Filial: {employee['branch_name']}\n"
                                f"📷 Natija turi: Rasm",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\nIltimos, qaytadan urinib ko'ring.",
            reply_markup=get_user_menu()
        )

    await state.clear()


@router.message(TaskSubmission.waiting_photo)
async def process_invalid_photo(message: Message, state: FSMContext):
    """Noto'g'ri fayl turi"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_menu())
        return

    await message.answer(
        "❌ Iltimos, faqat rasm yuboring!",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "cancel_submit")
async def cancel_submit(callback: CallbackQuery, state: FSMContext):
    """Natija yuborishni bekor qilish"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Bekor qilindi.", reply_markup=get_user_menu())
    await callback.answer()


@router.callback_query(F.data == "already_done")
async def already_done(callback: CallbackQuery):
    """Vazifa allaqachon bajarilgan"""
    await callback.answer("✅ Siz bu vazifani allaqachon bajargansiz!", show_alert=True)


# ============= PROFIL =============

@router.message(F.text == "👤 Profilim")
async def show_profile(message: Message):
    """Profil ma'lumotlarini ko'rsatish"""
    user_id = message.from_user.id

    # Admin tekshiruvi
    if user_id in ADMIN_IDS:
        await message.answer("Siz adminsiz. /admin buyrug'ini ishlating.")
        return

    employee = await db.get_employee_by_telegram_id(user_id)

    if not employee:
        await message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz!\n"
            "/start buyrug'ini yuboring."
        )
        return

    shift_name = SHIFTS.get(employee['shift'], employee['shift'])

    text = (
        f"👤 <b>Mening profilim</b>\n\n"
        f"📝 Ism: {employee['first_name']} {employee['last_name']}\n"
        f"🏢 Filial: {employee['branch_name']}\n"
        f"⏰ Smena: {shift_name}\n"
        f"📊 Status: {'✅ Faol' if employee['is_active'] else '❌ Faol emas'}\n"
    )

    await message.answer(text, reply_markup=get_profile_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "profile_edit")
async def callback_profile_edit(callback: CallbackQuery):
    """Profilni tahrirlash menyusi"""
    await callback.message.edit_text(
        "✏️ <b>Profilni tahrirlash</b>\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=get_profile_edit_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "profile_back")
async def callback_profile_back(callback: CallbackQuery, state: FSMContext):
    """Profilga qaytish"""
    await state.clear()

    user_id = callback.from_user.id
    employee = await db.get_employee_by_telegram_id(user_id)

    if not employee:
        await callback.message.edit_text("❌ Xatolik yuz berdi.")
        await callback.answer()
        return

    shift_name = SHIFTS.get(employee['shift'], employee['shift'])

    text = (
        f"👤 <b>Mening profilim</b>\n\n"
        f"📝 Ism: {employee['first_name']} {employee['last_name']}\n"
        f"🏢 Filial: {employee['branch_name']}\n"
        f"⏰ Smena: {shift_name}\n"
        f"📊 Status: {'✅ Faol' if employee['is_active'] else '❌ Faol emas'}\n"
    )

    await callback.message.edit_text(text, reply_markup=get_profile_keyboard(), parse_mode="HTML")
    await callback.answer()


# ============= ISM VA FAMILIYANI TAHRIRLASH =============

@router.callback_query(F.data == "edit_name")
async def callback_edit_name(callback: CallbackQuery, state: FSMContext):
    """Ism va familiyani tahrirlash"""
    await callback.message.answer(
        "✏️ <b>Ism va familiyani o'zgartirish</b>\n\n"
        "Yangi ism va familiyangizni kiriting (masalan: Aziz Azizov):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProfileEdit.editing_name)
    await callback.answer()


@router.message(ProfileEdit.editing_name)
async def process_edit_name(message: Message, state: FSMContext):
    """Yangi ism va familiyani qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_user_menu())
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer(
            "❌ Iltimos, ism va familiyani to'liq kiriting!\n"
            "Masalan: Aziz Azizov",
            reply_markup=get_cancel_keyboard()
        )
        return

    first_name = parts[0]
    last_name = ' '.join(parts[1:])

    try:
        await db.update_employee_by_telegram_id(
            telegram_id=message.from_user.id,
            first_name=first_name,
            last_name=last_name
        )

        await message.answer(
            f"✅ <b>Ma'lumotlar yangilandi!</b>\n\n"
            f"Yangi ism: {first_name} {last_name}",
            reply_markup=get_user_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=get_user_menu()
        )

    await state.clear()


# ============= FILIALNI TAHRIRLASH =============

@router.callback_query(F.data == "edit_branch")
async def callback_edit_branch(callback: CallbackQuery, state: FSMContext):
    """Filialni tahrirlash"""
    branches = await db.get_all_branches()

    if not branches:
        await callback.answer("❌ Filiallar mavjud emas!", show_alert=True)
        return

    await callback.message.edit_text(
        "🏢 <b>Yangi filialni tanlang:</b>",
        reply_markup=get_branch_select_keyboard(branches),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_branch_"))
async def callback_select_branch(callback: CallbackQuery):
    """Filial tanlash"""
    branch_id = int(callback.data.split("_")[2])

    try:
        await db.update_employee_by_telegram_id(
            telegram_id=callback.from_user.id,
            branch_id=branch_id
        )

        branch = await db.get_branch(branch_id)
        branch_name = branch['name'] if branch else "Noma'lum"

        await callback.message.edit_text(
            f"✅ <b>Filial o'zgartirildi!</b>\n\n"
            f"Yangi filial: {branch_name}",
            parse_mode="HTML"
        )
        await callback.answer("✅ Filial yangilandi!")

    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


# ============= SMENANI TAHRIRLASH =============

@router.callback_query(F.data == "edit_shift")
async def callback_edit_shift(callback: CallbackQuery):
    """Smenani tahrirlash"""
    await callback.message.edit_text(
        "⏰ <b>Yangi smenani tanlang:</b>",
        reply_markup=get_shift_select_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_shift_"))
async def callback_select_shift(callback: CallbackQuery):
    """Smena tanlash"""
    shift_key = callback.data.replace("select_shift_", "")

    if shift_key not in ["kunduzgi", "kechki"]:
        await callback.answer("❌ Noto'g'ri smena!", show_alert=True)
        return

    try:
        await db.update_employee_by_telegram_id(
            telegram_id=callback.from_user.id,
            shift=shift_key
        )

        shift_name = SHIFTS.get(shift_key, shift_key)

        await callback.message.edit_text(
            f"✅ <b>Smena o'zgartirildi!</b>\n\n"
            f"Yangi smena: {shift_name}",
            parse_mode="HTML"
        )
        await callback.answer("✅ Smena yangilandi!")

    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.callback_query(F.data == "cancel_edit")
async def callback_cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Tahrirlashni bekor qilish"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("❌ Bekor qilindi.")