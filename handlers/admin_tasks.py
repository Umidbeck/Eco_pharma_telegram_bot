"""
Admin - Vazifalar boshqaruvi va Hisobotlar (CRUD)
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import ADMIN_IDS
from database import db
from keyboards import admin_kb
from utils import helpers

router = Router()
logger = logging.getLogger(__name__)


class TaskEditStates(StatesGroup):
    editing_title = State()
    editing_description = State()
    editing_start_time = State()
    editing_deadline = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============== VAZIFALAR RO'YXATI (CRUD) ==============

@router.message(F.text == "📝 Vazifalar ro'yxati")
async def tasks_list_menu(message: Message):
    """Vazifalar ro'yxatini ko'rsatish"""
    if not is_admin(message.from_user.id):
        return

    tasks = await db.get_active_tasks()

    if not tasks:
        await message.answer(
            "📭 <b>Faol vazifalar yo'q</b>\n\n"
            "Yangi vazifa yaratish uchun '📋 Vazifa yaratish' tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"📝 <b>Vazifalar</b> ({len(tasks)} ta)\n\n"
        f"Boshqarish uchun vazifani tanlang:",
        reply_markup=admin_kb.get_tasks_list_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tasks_list_back")
async def tasks_list_back(callback: CallbackQuery):
    """Vazifalar ro'yxatiga qaytish"""
    if not is_admin(callback.from_user.id):
        return

    tasks = await db.get_active_tasks()

    if not tasks:
        await callback.message.edit_text(
            "📭 <b>Faol vazifalar yo'q</b>\n\n"
            "Yangi vazifa yaratish uchun '📋 Vazifa yaratish' tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        f"📝 <b>Vazifalar</b> ({len(tasks)} ta)\n\n"
        f"Boshqarish uchun vazifani tanlang:",
        reply_markup=admin_kb.get_tasks_list_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("task_manage_"))
async def task_manage(callback: CallbackQuery):
    """Vazifa boshqaruv sahifasi"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    branches = await db.get_task_branches(task_id)
    branch_names = ", ".join([b['name'] for b in branches]) or "Tanlangan filiallar yo'q"

    text = f"📋 <b>{task['title']}</b>\n\n"
    text += f"📄 <b>Tavsif:</b> {task['description']}\n\n"
    text += f"🏢 <b>Filiallar:</b> {branch_names}\n"
    text += f"⏰ <b>Smena:</b> {helpers.get_shift_name(task['shift'])}\n"
    text += f"📋 <b>Tur:</b> {helpers.get_task_type_name(task['task_type'])}\n"
    text += f"📤 <b>Natija turi:</b> {helpers.get_result_type_name(task['result_type'])}\n\n"
    text += f"🕐 <b>Boshlanish:</b> {helpers.format_datetime(task['start_time'])}\n"
    text += f"⏰ <b>Deadline:</b> {helpers.format_datetime(task['deadline'])}"

    await callback.message.edit_text(
        text,
        reply_markup=admin_kb.get_task_manage_keyboard(task_id),
        parse_mode="HTML"
    )


# ============== STATISTIKA ==============

@router.callback_query(F.data.startswith("task_stats_"))
async def task_stats(callback: CallbackQuery):
    """Vazifa statistikasi"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    stats = await db.get_task_statistics(task_id)

    text = f"📊 <b>Statistika</b>\n\n"
    text += f"📋 <b>{task['title']}</b>\n"
    text += f"⏰ Deadline: {helpers.format_datetime(task['deadline'])}\n\n"

    total_submitted = 0
    total_not_submitted = 0
    
    # Vazifa yuborgan va yubormaganlarni alohida ko'rsatish
    submitted_list = []
    not_submitted_list = []

    for bs in stats.get('branches', []):
        branch_name = bs['name']
        
        # Vazifa yuborgan xodimlar (vaqtida va kechikkan)
        all_submitted = bs.get('completed', []) + bs.get('late', [])
        
        for emp in all_submitted:
            result_info = emp.get('result')
            submitted_at = result_info.get('submitted_at') if result_info else 'N/A'
            submitted_list.append({
                'name': emp['name'],
                'branch': branch_name,
                'time': submitted_at,
                'is_late': result_info.get('is_late', 0) if result_info else 0
            })
            total_submitted += 1
        
        # Vazifa yubormagan xodimlar
        for emp in bs.get('not_completed', []):
            not_submitted_list.append({
                'name': emp['name'],
                'branch': branch_name
            })
            total_not_submitted += 1

    # Vazifa yuborganlar ro'yxati
    if submitted_list:
        text += "<b>✅ Vazifa yuborgan xodimlar:</b>\n\n"
        for emp in submitted_list:
            time_str = helpers.format_datetime(emp['time']) if emp['time'] != 'N/A' else 'N/A'
            status = " (⚠️ Kechikkan)" if emp['is_late'] else ""
            text += f"🏢 {emp['branch']}\n"
            text += f"👤 {emp['name']}{status}\n"
            text += f"🕐 {time_str}\n\n"
    
    # Vazifa yubormaganlar ro'yxati
    if not_submitted_list:
        text += "<b>❌ Vazifa yubormagan xodimlar:</b>\n\n"
        for emp in not_submitted_list:
            text += f"🏢 {emp['branch']}\n"
            text += f"👤 {emp['name']}\n\n"

    text += f"<b>Jami:</b>\n"
    text += f"✅ Yuborgan: {total_submitted} ta\n"
    text += f"❌ Yubormagan: {total_not_submitted} ta"

    await callback.message.edit_text(
        text,
        reply_markup=admin_kb.get_task_manage_keyboard(task_id),
        parse_mode="HTML"
    )


# ============== NATIJALARNI KO'RISH ==============

@router.callback_query(F.data.startswith("task_results_"))
async def task_results(callback: CallbackQuery, bot: Bot):
    """Vazifa natijalari"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    results = await db.get_all_task_results(task_id)

    if not results:
        await callback.answer("📭 Hali natijalar yo'q!", show_alert=True)
        return

    await callback.message.edit_text(
        f"📊 <b>Natijalar</b>\n\n"
        f"📋 {task['title']}\n"
        f"Jami: {len(results)} ta natija",
        reply_markup=admin_kb.get_task_results_keyboard(task_id, results),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_result_"))
async def view_result(callback: CallbackQuery, bot: Bot):
    """Natijani ko'rish"""
    if not is_admin(callback.from_user.id):
        return

    result_id = int(callback.data.split("_")[2])

    result = await db.get_task_result_by_id(result_id)

    if not result:
        await callback.answer("❌ Natija topilmadi!", show_alert=True)
        return

    late = " (⚠️ Kechiktirilgan)" if result['is_late'] else ""

    if result['result_photo_id']:
        await bot.send_photo(
            callback.from_user.id,
            result['result_photo_id'],
            caption=f"📷 <b>Rasm natija</b>{late}\n\n"
                    f"👤 Xodim: {result['first_name']} {result['last_name']}\n"
                    f"🏢 Filial: {result['branch_name']}\n"
                    f"📋 Vazifa: {result['title']}",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.message.edit_text(
            f"📝 <b>Matn natija</b>{late}\n\n"
            f"👤 Xodim: {result['first_name']} {result['last_name']}\n"
            f"🏢 Filial: {result['branch_name']}\n"
            f"📋 Vazifa: {result['title']}\n\n"
            f"💬 <b>Natija:</b>\n{result['result_text']}",
            reply_markup=admin_kb.get_result_view_keyboard(result['task_id']),
            parse_mode="HTML"
        )


# ============== O'CHIRISH ==============

@router.callback_query(F.data.startswith("task_delete_"))
async def task_delete(callback: CallbackQuery):
    """Vazifani o'chirish so'rovi"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 <b>Vazifani o'chirish</b>\n\n"
        f"📋 {task['title']}\n\n"
        f"⚠️ Bu amalni qaytarib bo'lmaydi!\n"
        f"Barcha natijalar ham o'chiriladi.\n\n"
        f"Davom etishni xohlaysizmi?",
        reply_markup=admin_kb.get_confirm_task_delete(task_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("confirm_task_delete_"))
async def confirm_task_delete(callback: CallbackQuery):
    """Vazifani o'chirishni tasdiqlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[3])

    await db.delete_task(task_id)

    await callback.message.edit_text(
        "✅ <b>Vazifa muvaffaqiyatli o'chirildi!</b>",
        parse_mode="HTML"
    )
    await callback.answer("✅ O'chirildi!")


# ============== TAHRIRLASH ==============

@router.callback_query(F.data.startswith("task_edit_"))
async def task_edit(callback: CallbackQuery):
    """Vazifa tahrirlash menyusi"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer("❌ Vazifa topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"✏️ <b>Tahrirlash</b>\n\n"
        f"📋 {task['title']}\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=admin_kb.get_task_edit_keyboard(task_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_task_title_"))
async def edit_task_title(callback: CallbackQuery, state: FSMContext):
    """Sarlavhani tahrirlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[3])
    await state.update_data(editing_task_id=task_id)
    await state.set_state(TaskEditStates.editing_title)

    await callback.message.edit_text(
        "📝 <b>Yangi sarlavha kiriting:</b>",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskEditStates.editing_title)
async def process_edit_title(message: Message, state: FSMContext):
    """Yangi sarlavhani saqlash"""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    await db.update_task(data['editing_task_id'], title=message.text)
    await state.clear()

    await message.answer(
        f"✅ <b>Sarlavha yangilandi!</b>\n\n"
        f"Yangi sarlavha: {message.text}",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_task_desc_"))
async def edit_task_desc(callback: CallbackQuery, state: FSMContext):
    """Tavsifni tahrirlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[3])
    await state.update_data(editing_task_id=task_id)
    await state.set_state(TaskEditStates.editing_description)

    await callback.message.edit_text(
        "📄 <b>Yangi tavsif kiriting:</b>",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskEditStates.editing_description)
async def process_edit_desc(message: Message, state: FSMContext):
    """Yangi tavsifni saqlash"""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    await db.update_task(data['editing_task_id'], description=message.text)
    await state.clear()

    await message.answer(
        "✅ <b>Tavsif yangilandi!</b>",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_task_start_"))
async def edit_task_start(callback: CallbackQuery, state: FSMContext):
    """Boshlanish vaqtini tahrirlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[3])
    await state.update_data(editing_task_id=task_id)
    await state.set_state(TaskEditStates.editing_start_time)

    await callback.message.edit_text(
        "🕐 <b>Yangi boshlanish vaqti</b>\n\n"
        "Format: <code>DD.MM.YYYY HH:MM</code>\n"
        "Misol: <code>15.01.2025 09:00</code>\n\n"
        "Yoki faqat soat: <code>HH:MM</code>",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskEditStates.editing_start_time)
async def process_edit_start(message: Message, state: FSMContext):
    """Yangi boshlanish vaqtini saqlash"""
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()
    start_time = None

    if ':' in text and len(text) <= 5:
        start_time = helpers.parse_time(text)
    else:
        parts = text.split()
        if len(parts) == 2:
            start_time = helpers.parse_datetime(parts[0], parts[1])

    if not start_time:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Format: DD.MM.YYYY HH:MM\n"
            "Yoki faqat soat: HH:MM"
        )
        return

    data = await state.get_data()
    await db.update_task(data['editing_task_id'], start_time=start_time)
    await state.clear()

    await message.answer(
        f"✅ <b>Boshlanish vaqti yangilandi!</b>\n\n"
        f"Yangi vaqt: {helpers.format_datetime(start_time)}",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_task_deadline_"))
async def edit_task_deadline(callback: CallbackQuery, state: FSMContext):
    """Deadline tahrirlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[3])
    await state.update_data(editing_task_id=task_id)
    await state.set_state(TaskEditStates.editing_deadline)

    await callback.message.edit_text(
        "⏰ <b>Yangi deadline</b>\n\n"
        "Format: <code>DD.MM.YYYY HH:MM</code>\n"
        "Misol: <code>15.01.2025 18:00</code>\n\n"
        "Yoki faqat soat: <code>HH:MM</code>",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskEditStates.editing_deadline)
async def process_edit_deadline(message: Message, state: FSMContext):
    """Yangi deadline saqlash"""
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()
    deadline = None

    if ':' in text and len(text) <= 5:
        deadline = helpers.parse_time(text)
    else:
        parts = text.split()
        if len(parts) == 2:
            deadline = helpers.parse_datetime(parts[0], parts[1])

    if not deadline:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Format: DD.MM.YYYY HH:MM\n"
            "Yoki faqat soat: HH:MM"
        )
        return

    data = await state.get_data()
    await db.update_task(data['editing_task_id'], deadline=deadline)
    await state.clear()

    await message.answer(
        f"✅ <b>Deadline yangilandi!</b>\n\n"
        f"Yangi deadline: {helpers.format_datetime(deadline)}",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


# ============== HISOBOTLAR ==============

@router.message(F.text == "📈 Hisobotlar")
async def reports_menu(message: Message):
    """Hisobotlar menyusi"""
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📈 <b>Hisobotlar</b>\n\n"
        "Kerakli hisobot turini tanlang:",
        reply_markup=admin_kb.get_reports_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "reports_menu")
async def reports_menu_callback(callback: CallbackQuery):
    """Hisobotlar menyusiga qaytish"""
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "📈 <b>Hisobotlar</b>\n\n"
        "Kerakli hisobot turini tanlang:",
        reply_markup=admin_kb.get_reports_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "report_active_tasks")
async def report_active_tasks(callback: CallbackQuery):
    """Faol vazifalar hisoboti"""
    if not is_admin(callback.from_user.id):
        return

    tasks = await db.get_active_tasks()

    if not tasks:
        await callback.message.edit_text(
            "📭 Faol vazifalar yo'q.",
            reply_markup=admin_kb.get_reports_menu()
        )
        return

    await callback.message.edit_text(
        f"📋 <b>Faol vazifalar</b> ({len(tasks)} ta)\n\n"
        f"Batafsil ko'rish uchun tanlang:",
        reply_markup=admin_kb.get_active_tasks_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "report_task_stats")
async def report_task_stats(callback: CallbackQuery):
    """Vazifa statistikasi hisoboti"""
    if not is_admin(callback.from_user.id):
        return

    tasks = await db.get_active_tasks()

    if not tasks:
        await callback.message.edit_text(
            "📭 Vazifalar yo'q.",
            reply_markup=admin_kb.get_reports_menu()
        )
        return

    await callback.message.edit_text(
        f"📊 <b>Statistika</b> ({len(tasks)} ta vazifa)\n\n"
        f"Batafsil ko'rish uchun vazifani tanlang:",
        reply_markup=admin_kb.get_active_tasks_keyboard(tasks),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("report_task_"))
async def report_task_details(callback: CallbackQuery):
    """Vazifa hisoboti - bajarganlar/bajarmaganlar tanlash"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer(
            "❌ Vazifa topilmadi!", show_alert=True
        )
        return

    stats = await db.get_task_statistics(task_id)

    total_submitted = 0
    total_not_submitted = 0

    for bs in stats.get("branches", []):
        all_submitted = (
            bs.get("completed", []) + bs.get("late", [])
        )
        total_submitted += len(all_submitted)
        total_not_submitted += len(
            bs.get("not_completed", [])
        )

    msg = (
        f"📋 <b>{task['title']}</b>\n"
        f"⏰ Deadline: "
        f"{helpers.format_datetime(task['deadline'])}\n\n"
        f"✅ Bajarganlar: {total_submitted} ta\n"
        f"❌ Bajarmaganlar: {total_not_submitted} ta\n\n"
        f"Batafsil ko'rish uchun tanlang:"
    )

    await callback.message.edit_text(
        msg,
        reply_markup=admin_kb.get_task_report_options_keyboard(
            task_id
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("report_submitted_"))
async def report_submitted(callback: CallbackQuery):
    """Vazifani bajargan xodimlar ro'yxati"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer(
            "❌ Vazifa topilmadi!", show_alert=True
        )
        return

    stats = await db.get_task_statistics(task_id)

    msg = (
        f"📋 <b>{task['title']}</b>\n"
        f"⏰ Deadline: "
        f"{helpers.format_datetime(task['deadline'])}\n\n"
        f"<b>✅ Vazifa yuborgan xodimlar:</b>\n\n"
    )

    count = 0
    for bs in stats.get("branches", []):
        branch_name = bs["name"]
        all_submitted = (
            bs.get("completed", []) + bs.get("late", [])
        )
        for emp in all_submitted:
            result_info = emp.get("result")
            submitted_at = (
                result_info.get("submitted_at")
                if result_info
                else "N/A"
            )
            is_late = (
                result_info.get("is_late", 0)
                if result_info
                else 0
            )
            time_str = (
                helpers.format_datetime(submitted_at)
                if submitted_at != "N/A"
                else "N/A"
            )
            status = " (⚠️ Kechikkan)" if is_late else ""
            msg += (
                f"🏢 {branch_name}\n"
                f"👤 {emp['name']}{status}\n"
                f"🕐 {time_str}\n\n"
            )
            count += 1

    if count == 0:
        msg += "Hali hech kim bajarmagan.\n"

    msg += f"\n<b>Jami:</b> {count} ta"

    await callback.message.edit_text(
        msg,
        reply_markup=admin_kb.get_task_report_back_keyboard(
            task_id
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("report_notdone_"))
async def report_not_done(callback: CallbackQuery):
    """Vazifani bajarmagan xodimlar ro'yxati"""
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split("_")[2])
    task = await db.get_task(task_id)

    if not task:
        await callback.answer(
            "❌ Vazifa topilmadi!", show_alert=True
        )
        return

    stats = await db.get_task_statistics(task_id)

    msg = (
        f"📋 <b>{task['title']}</b>\n"
        f"⏰ Deadline: "
        f"{helpers.format_datetime(task['deadline'])}\n\n"
        f"<b>❌ Vazifa yubormagan xodimlar:</b>\n\n"
    )

    count = 0
    for bs in stats.get("branches", []):
        branch_name = bs["name"]
        for emp in bs.get("not_completed", []):
            msg += (
                f"🏢 {branch_name}\n"
                f"👤 {emp['name']}\n\n"
            )
            count += 1

    if count == 0:
        msg += "Barcha xodimlar bajargan!\n"

    msg += f"\n<b>Jami:</b> {count} ta"

    await callback.message.edit_text(
        msg,
        reply_markup=admin_kb.get_task_report_back_keyboard(
            task_id
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_reports")
async def back_to_reports(callback: CallbackQuery):
    """Hisobotlarga qaytish"""
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "📈 <b>Hisobotlar</b>",
        reply_markup=admin_kb.get_reports_menu(),
        parse_mode="HTML"
    )