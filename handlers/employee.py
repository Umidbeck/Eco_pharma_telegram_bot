from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import db
from keyboards import employee_kb, admin_kb
from utils import helpers

router = Router()


class RegisterStates(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    selecting_branch = State()
    selecting_shift = State()
    confirming = State()


class EditStates(StatesGroup):
    waiting_name = State()
    selecting_branch = State()
    selecting_shift = State()


class SubmitStates(StatesGroup):
    waiting_text = State()
    waiting_photo = State()


# ============== START ==============

@router.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id

    # Admin bo'lsa
    if user_id in ADMIN_IDS:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{message.from_user.first_name}</b>!\n\n"
            f"Siz admin sifatida tizimga kirdingiz.\n"
            f"Admin panelni ochish uchun /admin buyrug'ini kiriting.",
            reply_markup=admin_kb.get_admin_main_menu(),
            parse_mode="HTML"
        )
        return

    # Xodim bo'lsa
    employee = await db.get_employee_by_telegram_id(user_id)

    if employee:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{employee['first_name']}</b>!\n\n"
            f"🏢 Filial: {employee['branch_name']}\n"
            f"⏰ Smena: {helpers.get_shift_name(employee['shift'])}\n\n"
            f"Quyidagi menyu orqali harakat qiling:",
            reply_markup=employee_kb.get_employee_main_menu(),
            parse_mode="HTML"
        )
    else:
        branches = await db.get_all_branches()
        if not branches:
            await message.answer(
                "⚠️ Hozircha tizimda filiallar mavjud emas.\n"
                "Iltimos, keyinroq urinib ko'ring."
            )
            return

        await message.answer(
            f"👋 Xush kelibsiz, <b>{message.from_user.first_name}</b>!\n\n"
            f"Tizimdan foydalanish uchun ro'yxatdan o'ting:",
            reply_markup=employee_kb.get_register_menu(),
            parse_mode="HTML"
        )


# ============== RO'YXATDAN O'TISH ==============

@router.callback_query(F.data == "register_start")
async def register_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegisterStates.waiting_first_name)
    await callback.message.edit_text(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Ismingizni kiriting:",
        parse_mode="HTML"
    )


@router.message(RegisterStates.waiting_first_name)
async def register_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await state.set_state(RegisterStates.waiting_last_name)
    await message.answer("Familiyangizni kiriting:")


@router.message(RegisterStates.waiting_last_name)
async def register_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await state.set_state(RegisterStates.selecting_branch)

    branches = await db.get_all_branches()
    await message.answer(
        "🏢 Filialingizni tanlang:",
        reply_markup=employee_kb.get_branches_for_register(branches)
    )


@router.callback_query(F.data.startswith("reg_branch_"), RegisterStates.selecting_branch)
async def register_branch_selected(callback: CallbackQuery, state: FSMContext):
    branch_id = int(callback.data.split("_")[2])
    branch = await db.get_branch(branch_id)

    await state.update_data(branch_id=branch_id, branch_name=branch['name'])
    await state.set_state(RegisterStates.selecting_shift)

    await callback.message.edit_text(
        "⏰ Smenangizni tanlang:",
        reply_markup=employee_kb.get_shift_for_register()
    )


@router.callback_query(F.data.startswith("reg_shift_"), RegisterStates.selecting_shift)
async def register_shift_selected(callback: CallbackQuery, state: FSMContext):
    shift = callback.data.split("_")[2]
    await state.update_data(shift=shift)
    await state.set_state(RegisterStates.confirming)

    data = await state.get_data()

    await callback.message.edit_text(
        f"📝 <b>Ma'lumotlaringizni tasdiqlang:</b>\n\n"
        f"👤 Ism: {data['first_name']}\n"
        f"👤 Familiya: {data['last_name']}\n"
        f"🏢 Filial: {data['branch_name']}\n"
        f"⏰ Smena: {helpers.get_shift_name(shift)}",
        reply_markup=employee_kb.get_confirm_register(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "reg_confirm", RegisterStates.confirming)
async def register_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    try:
        await db.create_employee(
            telegram_id=callback.from_user.id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            branch_id=data['branch_id'],
            shift=data['shift']
        )

        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
            f"👋 Xush kelibsiz, {data['first_name']}!\n\n"
            f"Endi vazifalaringizni ko'rishingiz mumkin.",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "Quyidagi menyu orqali harakat qiling:",
            reply_markup=employee_kb.get_employee_main_menu()
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: Siz allaqachon ro'yxatdan o'tgansiz yoki tizimda xatolik mavjud.",
        )
        await state.clear()


@router.callback_query(F.data == "reg_cancel")
async def register_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Ro'yxatdan o'tish bekor qilindi.\n\n"
        "Qayta urinish uchun /start buyrug'ini kiriting."
    )


# ============== PROFIL ==============

@router.message(F.text == "👤 Profilim")
async def profile_view(message: Message):
    employee = await db.get_employee_by_telegram_id(message.from_user.id)

    if not employee:
        await message.answer(
            "⚠️ Siz ro'yxatdan o'tmagansiz.\n"
            "Ro'yxatdan o'tish uchun /start buyrug'ini kiriting."
        )
        return

    await message.answer(
        f"👤 <b>Sizning profilingiz</b>\n\n"
        f"👤 Ism: {employee['first_name']}\n"
        f"👤 Familiya: {employee['last_name']}\n"
        f"🏢 Filial: {employee['branch_name']}\n"
        f"⏰ Smena: {helpers.get_shift_name(employee['shift'])}\n"
        f"📅 Ro'yxatdan o'tgan: {helpers.format_datetime(employee['created_at'])}",
        reply_markup=employee_kb.get_profile_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "profile_edit")
async def profile_edit(callback: CallbackQuery):
    await callback.message.edit_text(
        "✏️ <b>Profilni tahrirlash</b>\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=employee_kb.get_profile_edit_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditStates.waiting_name)
    await callback.message.edit_text(
        "📝 Yangi ism va familiyangizni kiriting:\n"
        "(Masalan: Alisher Navoiy)",
        reply_markup=employee_kb.get_cancel_keyboard()
    )


@router.message(EditStates.waiting_name)
async def edit_name_received(message: Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Iltimos, ism va familiyani kiriting (masalan: Alisher Navoiy)")
        return

    first_name, last_name = parts[0], parts[1]
    employee = await db.get_employee_by_telegram_id(message.from_user.id)

    await db.update_employee(
        employee['id'],
        first_name=first_name,
        last_name=last_name,
        branch_id=employee['branch_id'],
        shift=employee['shift']
    )

    await state.clear()
    await message.answer(
        f"✅ Ism va familiya yangilandi!\n\n"
        f"👤 Yangi ism: {first_name} {last_name}",
        reply_markup=employee_kb.get_employee_main_menu()
    )


@router.callback_query(F.data == "edit_branch")
async def edit_branch_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditStates.selecting_branch)
    branches = await db.get_all_branches()
    await callback.message.edit_text(
        "🏢 Yangi filialni tanlang:",
        reply_markup=employee_kb.get_branches_for_register(branches)
    )


@router.callback_query(F.data.startswith("reg_branch_"), EditStates.selecting_branch)
async def edit_branch_selected(callback: CallbackQuery, state: FSMContext):
    branch_id = int(callback.data.split("_")[2])
    branch = await db.get_branch(branch_id)
    employee = await db.get_employee_by_telegram_id(callback.from_user.id)

    await db.update_employee(
        employee['id'],
        first_name=employee['first_name'],
        last_name=employee['last_name'],
        branch_id=branch_id,
        shift=employee['shift']
    )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Filial yangilandi!\n\n"
        f"🏢 Yangi filial: {branch['name']}"
    )
    await callback.message.answer(
        "Menyu:",
        reply_markup=employee_kb.get_employee_main_menu()
    )


@router.callback_query(F.data == "edit_shift")
async def edit_shift_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditStates.selecting_shift)
    await callback.message.edit_text(
        "⏰ Yangi smenani tanlang:",
        reply_markup=employee_kb.get_shift_for_register()
    )


@router.callback_query(F.data.startswith("reg_shift_"), EditStates.selecting_shift)
async def edit_shift_selected(callback: CallbackQuery, state: FSMContext):
    shift = callback.data.split("_")[2]
    employee = await db.get_employee_by_telegram_id(callback.from_user.id)

    await db.update_employee(
        employee['id'],
        first_name=employee['first_name'],
        last_name=employee['last_name'],
        branch_id=employee['branch_id'],
        shift=shift
    )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Smena yangilandi!\n\n"
        f"⏰ Yangi smena: {helpers.get_shift_name(shift)}"
    )
    await callback.message.answer(
        "Menyu:",
        reply_markup=employee_kb.get_employee_main_menu()
    )


@router.callback_query(F.data == "profile_back")
async def profile_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    employee = await db.get_employee_by_telegram_id(callback.from_user.id)

    await callback.message.edit_text(
        f"👤 <b>Sizning profilingiz</b>\n\n"
        f"👤 Ism: {employee['first_name']}\n"
        f"👤 Familiya: {employee['last_name']}\n"
        f"🏢 Filial: {employee['branch_name']}\n"
        f"⏰ Smena: {helpers.get_shift_name(employee['shift'])}\n"
        f"📅 Ro'yxatdan o'tgan: {helpers.format_datetime(employee['created_at'])}",
        reply_markup=employee_kb.get_profile_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "profile_delete")
async def profile_delete(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗑 <b>Profilni o'chirish</b>\n\n"
        "⚠️ Diqqat! Bu amal qaytarilmaydi.\n"
        "Barcha ma'lumotlaringiz o'chiriladi.\n\n"
        "Davom etishni xohlaysizmi?",
        reply_markup=employee_kb.get_confirm_delete_profile(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_delete_profile")
async def confirm_delete_profile(callback: CallbackQuery):
    employee = await db.get_employee_by_telegram_id(callback.from_user.id)
    await db.delete_employee(employee['id'])

    await callback.message.edit_text(
        "✅ Profilingiz muvaffaqiyatli o'chirildi.\n\n"
        "Qayta ro'yxatdan o'tish uchun /start buyrug'ini kiriting."
    )


# ============== VAZIFALAR ==============

@router.message(F.text == "📋 Vazifalarim")
async def my_tasks(message: Message):
    employee = await db.get_employee_by_telegram_id(message.from_user.id)

    if not employee:
        await message.answer(
            "⚠️ Siz ro'yxatdan o'tmagansiz.\n"
            "Ro'yxatdan o'tish uchun /start buyrug'ini kiriting."
        )
        return

    tasks = await db.get_employee_tasks(employee['id'])

    text = "📋 <b>Sizning vazifalaringiz</b>\n\n"

    if not tasks:
        text += "📭 Hozircha sizga vazifa berilmagan."
    else:
        pending = [t for t in tasks if not t.get('is_completed')]
        completed = [t for t in tasks if t.get('is_completed')]

        text += f"⏳ Kutilayotgan: {len(pending)} ta\n"
        text += f"✅ Bajarilgan: {len(completed)} ta\n\n"
        text += "Batafsil ko'rish uchun vazifani tanlang:"

    await message.answer(
        text,
        reply_markup=employee_kb.get_tasks_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    employee = await db.get_employee_by_telegram_id(callback.from_user.id)
    tasks = await db.get_employee_tasks(employee['id'])

    text = "📋 <b>Sizning vazifalaringiz</b>\n\n"

    if not tasks:
        text += "📭 Hozircha sizga vazifa berilmagan."
    else:
        pending = [t for t in tasks if not t.get('is_completed')]
        completed = [t for t in tasks if t.get('is_completed')]

        text += f"⏳ Kutilayotgan: {len(pending)} ta\n"
        text += f"✅ Bajarilgan: {len(completed)} ta"

    await callback.message.edit_text(
        text,
        reply_markup=employee_kb.get_tasks_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("emp_task_"))
async def view_task(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    employee = await db.get_employee_by_telegram_id(callback.from_user.id)
    result = await db.get_task_result(task_id, employee['id'])
    is_completed = result is not None

    from datetime import datetime
    deadline = datetime.fromisoformat(task['deadline'])
    time_left = helpers.time_until(deadline)

    status_text = ""
    if is_completed:
        if result.get('is_late'):
            status_text = "⚠️ <b>Holat: Kechiktirilgan</b>"
        else:
            status_text = "✅ <b>Holat: Bajarilgan</b>"
    else:
        status_text = f"⏳ <b>Holat: Kutilmoqda</b>\n⏱ Qolgan vaqt: {time_left}"

    text = f"📋 <b>{task['title']}</b>\n\n"
    text += f"📄 {task['description']}\n\n"
    text += f"📋 Tur: {helpers.get_task_type_name(task['task_type'])}\n"
    text += f"📤 Natija turi: {helpers.get_result_type_name(task['result_type'])}\n"
    text += f"⏰ Deadline: {helpers.format_datetime(deadline)}\n\n"
    text += status_text

    await callback.message.edit_text(
        text,
        reply_markup=employee_kb.get_task_action_keyboard(task_id, is_completed, task['result_type']),
        parse_mode="HTML"
    )


# ============== NATIJA YUBORISH ==============

@router.callback_query(F.data.startswith("submit_text_"))
async def submit_text_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await state.set_state(SubmitStates.waiting_text)

    await callback.message.edit_text(
        "📝 <b>Natija yuborish</b>\n\n"
        "Natijangizni matn ko'rinishida yuboring:",
        reply_markup=employee_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_text)
async def submit_text_received(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data['task_id']

    employee = await db.get_employee_by_telegram_id(message.from_user.id)

    result_id, position, is_late = await db.submit_task_result(
        task_id=task_id,
        employee_id=employee['id'],
        result_text=message.text
    )

    await state.clear()

    position_emoji = helpers.get_position_emoji(position)

    await message.answer(
        f"✅ <b>Natija qabul qilindi!</b>\n\n"
        f"{position_emoji} Siz ushbu vazifani <b>{position}-bo'lib</b> bajardingiz!\n\n"
        f"Vazifalaringizga qaytish uchun '📋 Vazifalarim' tugmasini bosing.",
        reply_markup=employee_kb.get_employee_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("submit_photo_"))
async def submit_photo_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await state.set_state(SubmitStates.waiting_photo)

    await callback.message.edit_text(
        "📷 <b>Rasm yuborish</b>\n\n"
        "Natijangizni rasm ko'rinishida yuboring:\n\n"
        "⚠️ <i>Diqqat: Avval ishlatilgan rasmlar qabul qilinmaydi!</i>",
        reply_markup=employee_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_photo, F.photo)
async def submit_photo_received(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data['task_id']

    # Rasmning file_unique_id sini olish
    photo = message.photo[-1]  # Eng katta o'lcham
    file_unique_id = photo.file_unique_id

    # Rasm avval ishlatilganligini tekshirish
    if await db.check_photo_used(file_unique_id):
        await message.answer(
            "⚠️ <b>Bu rasm avval ishlatilgan!</b>\n\n"
            "Iltimos, boshqa rasm yuboring.",
            reply_markup=employee_kb.get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    employee = await db.get_employee_by_telegram_id(message.from_user.id)

    result_id, position, is_late = await db.submit_task_result(
        task_id=task_id,
        employee_id=employee['id'],
        file_unique_id=file_unique_id  # Faqat file_unique_id saqlanadi!
    )

    await state.clear()

    position_emoji = helpers.get_position_emoji(position)

    await message.answer(
        f"✅ <b>Rasm qabul qilindi!</b>\n\n"
        f"{position_emoji} Siz ushbu vazifani <b>{position}-bo'lib</b> bajardingiz!\n\n"
        f"Vazifalaringizga qaytish uchun '📋 Vazifalarim' tugmasini bosing.",
        reply_markup=employee_kb.get_employee_main_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_photo)
async def submit_photo_invalid(message: Message):
    await message.answer(
        "⚠️ Iltimos, rasm yuboring!",
        reply_markup=employee_kb.get_cancel_keyboard()
    )


@router.callback_query(F.data == "cancel_submit")
async def cancel_submit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Natija yuborish bekor qilindi.")

    employee = await db.get_employee_by_telegram_id(callback.from_user.id)
    tasks = await db.get_employee_tasks(employee['id'])

    await callback.message.answer(
        "📋 Vazifalaringiz:",
        reply_markup=employee_kb.get_tasks_keyboard(tasks)
    )


@router.callback_query(F.data == "already_done")
async def already_done(callback: CallbackQuery):
    await callback.answer("✅ Bu vazifa allaqachon bajarilgan!", show_alert=True)


@router.callback_query(F.data == "no_tasks")
async def no_tasks(callback: CallbackQuery):
    await callback.answer("📭 Hozircha vazifalar yo'q", show_alert=True)