"""
Admin - Filiallar, Vazifa yaratish, Statistika
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import logging

from config import ADMIN_IDS
from database import db
from keyboards import admin_kb
from utils import helpers

router = Router()
logger = logging.getLogger(__name__)


class BranchStates(StatesGroup):
    waiting_name = State()
    waiting_address = State()
    editing_name = State()
    editing_address = State()


class TaskStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    selecting_branches = State()
    selecting_shift = State()
    selecting_type = State()
    selecting_result_type = State()
    waiting_start_time = State()
    waiting_deadline = State()
    confirming = State()


# ============== ADMIN FILTER ==============

def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS


def is_admin_callback(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS


# ============== MAIN MENU ==============

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message):
        await message.answer("⛔️ Sizda admin huquqlari yo'q!")
        return

    await message.answer(
        "🔐 <b>Admin Panel</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "🏢 Filiallar")
async def branches_menu(message: Message):
    if not is_admin(message):
        return

    await message.answer(
        "🏢 <b>Filiallar boshqaruvi</b>\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=admin_kb.get_branches_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "branches_menu")
async def branches_menu_callback(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    await callback.message.edit_text(
        "🏢 <b>Filiallar boshqaruvi</b>\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=admin_kb.get_branches_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ============== FILIALLAR ==============

@router.callback_query(F.data == "branch_add")
async def branch_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    await state.set_state(BranchStates.waiting_name)
    await callback.message.edit_text(
        "🏢 <b>Yangi filial yaratish</b>\n\n"
        "📝 Filial nomini kiriting:",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(BranchStates.waiting_name)
async def branch_name_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    await state.update_data(name=message.text)
    await state.set_state(BranchStates.waiting_address)
    await message.answer(
        "📍 Filial manzilini kiriting (ixtiyoriy, o'tkazib yuborish uchun '-' kiriting):",
        reply_markup=admin_kb.get_cancel_keyboard()
    )


@router.message(BranchStates.waiting_address)
async def branch_address_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    data = await state.get_data()
    address = None if message.text == '-' else message.text

    try:
        branch_id = await db.create_branch(data['name'], address)
        await state.clear()
        await message.answer(
            f"✅ <b>Filial muvaffaqiyatli yaratildi!</b>\n\n"
            f"🏢 Nomi: {data['name']}\n"
            f"📍 Manzil: {address or 'Kiritilmagan'}\n"
            f"🆔 ID: {branch_id}",
            reply_markup=admin_kb.get_admin_main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Branch creation error: {e}")
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n"
            "Iltimos, qaytadan urinib ko'ring.",
            reply_markup=admin_kb.get_admin_main_menu()
        )
        await state.clear()


@router.callback_query(F.data == "branch_list")
async def branch_list(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    branches = await db.get_all_branches()

    if not branches:
        await callback.message.edit_text(
            "📭 Hozircha filiallar yo'q.\n"
            "Yangi filial qo'shish uchun '➕ Yangi filial' tugmasini bosing.",
            reply_markup=admin_kb.get_branches_menu()
        )
        return

    await callback.message.edit_text(
        f"🏢 <b>Filiallar ro'yxati</b>\n\n"
        f"Jami: {len(branches)} ta filial\n"
        f"Batafsil ko'rish uchun tanlang:",
        reply_markup=admin_kb.get_branches_list(branches),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("branch_view_"))
async def branch_view(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    branch_id = int(callback.data.split("_")[2])
    branch = await db.get_branch(branch_id)

    if not branch:
        await callback.answer("❌ Filial topilmadi!", show_alert=True)
        return

    employees_count = await db.get_branch_employees_count(branch_id)

    await callback.message.edit_text(
        f"🏢 <b>{branch['name']}</b>\n\n"
        f"📍 Manzil: {branch['address'] or 'Kiritilmagan'}\n"
        f"👥 Xodimlar soni: {employees_count} ta\n"
        f"📅 Yaratilgan: {helpers.format_datetime(branch['created_at'])}",
        reply_markup=admin_kb.get_branch_actions(branch_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("branch_edit_"))
async def branch_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    branch_id = int(callback.data.split("_")[2])
    await state.update_data(editing_branch_id=branch_id)
    await state.set_state(BranchStates.editing_name)

    branch = await db.get_branch(branch_id)
    await callback.message.edit_text(
        f"✏️ <b>Filialni tahrirlash</b>\n\n"
        f"Hozirgi nom: {branch['name']}\n\n"
        f"Yangi nomni kiriting (o'zgartirmaslik uchun '-' kiriting):",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(BranchStates.editing_name)
async def branch_edit_name(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    data = await state.get_data()
    branch = await db.get_branch(data['editing_branch_id'])

    new_name = branch['name'] if message.text == '-' else message.text
    await state.update_data(new_name=new_name)
    await state.set_state(BranchStates.editing_address)

    await message.answer(
        f"📍 Yangi manzilni kiriting (o'zgartirmaslik uchun '-' kiriting):\n"
        f"Hozirgi manzil: {branch['address'] or 'Kiritilmagan'}",
        reply_markup=admin_kb.get_cancel_keyboard()
    )


@router.message(BranchStates.editing_address)
async def branch_edit_address(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    data = await state.get_data()
    branch = await db.get_branch(data['editing_branch_id'])

    new_address = branch['address'] if message.text == '-' else message.text

    await db.update_branch(data['editing_branch_id'], data['new_name'], new_address)
    await state.clear()

    await message.answer(
        f"✅ <b>Filial muvaffaqiyatli yangilandi!</b>\n\n"
        f"🏢 Yangi nom: {data['new_name']}\n"
        f"📍 Yangi manzil: {new_address or 'Kiritilmagan'}",
        reply_markup=admin_kb.get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("branch_delete_"))
async def branch_delete(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    branch_id = int(callback.data.split("_")[2])
    branch = await db.get_branch(branch_id)

    await callback.message.edit_text(
        f"🗑 <b>Filialni o'chirish</b>\n\n"
        f"🏢 {branch['name']}\n\n"
        f"⚠️ Diqqat! Bu filialga tegishli barcha xodimlar ham o'chiriladi.\n"
        f"Davom etishni xohlaysizmi?",
        reply_markup=admin_kb.get_confirm_delete("branch", branch_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("branch_confirm_delete_"))
async def branch_confirm_delete(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    branch_id = int(callback.data.split("_")[3])
    await db.delete_branch(branch_id)

    await callback.message.edit_text(
        "✅ Filial muvaffaqiyatli o'chirildi!",
        reply_markup=admin_kb.get_branches_menu()
    )


@router.callback_query(F.data.startswith("branch_employees_"))
async def branch_employees(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return

    branch_id = int(callback.data.split("_")[2])
    branch = await db.get_branch(branch_id)
    employees = await db.get_employees_by_branch(branch_id)

    if not employees:
        await callback.message.edit_text(
            f"🏢 <b>{branch['name']}</b>\n\n"
            f"📭 Bu filialda xodimlar yo'q.",
            reply_markup=admin_kb.get_branch_actions(branch_id),
            parse_mode="HTML"
        )
        return

    text = f"🏢 <b>{branch['name']} - Xodimlar</b>\n\n"
    for i, emp in enumerate(employees, 1):
        shift = helpers.get_shift_name(emp['shift'])
        text += f"{i}. {emp['first_name']} {emp['last_name']} ({shift})\n"

    await callback.message.edit_text(
        text,
        reply_markup=admin_kb.get_branch_actions(branch_id),
        parse_mode="HTML"
    )


# ============== STATISTIKA ==============

@router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    if not is_admin(message):
        return

    branches = await db.get_all_branches()
    total_employees = await db.get_total_employees_count()

    text = "📊 <b>Statistika</b>\n\n"
    text += f"🏢 Jami filiallar: {len(branches)} ta\n"
    text += f"👥 Jami xodimlar: {total_employees} ta\n\n"

    if branches:
        text += "<b>Filiallar bo'yicha:</b>\n"
        for branch in branches:
            count = await db.get_branch_employees_count(branch['id'])
            text += f"  • {branch['name']}: {count} ta xodim\n"

    await message.answer(text, parse_mode="HTML")


# ============== VAZIFA YARATISH ==============

@router.message(F.text == "📋 Vazifa yaratish")
async def create_task_start(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    branches = await db.get_all_branches()
    if not branches:
        await message.answer(
            "⚠️ Avval filiallarni yarating!\n"
            "Vazifa yaratish uchun kamida bitta filial bo'lishi kerak."
        )
        return

    await state.clear()
    await state.set_state(TaskStates.waiting_title)
    await message.answer(
        "📋 <b>Yangi vazifa yaratish</b>\n\n"
        "📝 Vazifa sarlavhasini kiriting:",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskStates.waiting_title)
async def task_title_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    await state.update_data(title=message.text)
    await state.set_state(TaskStates.waiting_description)
    await message.answer(
        "📄 Vazifa tavsifini kiriting:",
        reply_markup=admin_kb.get_cancel_keyboard()
    )


@router.message(TaskStates.waiting_description)
async def task_description_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    await state.update_data(description=message.text, selected_branches=[])
    await state.set_state(TaskStates.selecting_branches)

    branches = await db.get_all_branches()
    await message.answer(
        "🏢 Vazifa uchun filiallarni tanlang:",
        reply_markup=admin_kb.get_task_branches_keyboard(branches, [])
    )


@router.callback_query(F.data == "task_branch_all", TaskStates.selecting_branches)
async def task_branch_all_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    data = await state.get_data()
    selected = data.get('selected_branches', [])
    branches = await db.get_all_branches()

    if len(selected) == len(branches):
        selected = []
    else:
        selected = [b['id'] for b in branches]

    await state.update_data(selected_branches=selected)
    await callback.message.edit_reply_markup(
        reply_markup=admin_kb.get_task_branches_keyboard(branches, selected)
    )


@router.callback_query(F.data.startswith("task_branch_"), TaskStates.selecting_branches)
async def task_branch_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    if callback.data == "task_branch_all":
        return

    data = await state.get_data()
    selected = data.get('selected_branches', [])
    branches = await db.get_all_branches()

    branch_id = int(callback.data.split("_")[2])
    if branch_id in selected:
        selected.remove(branch_id)
    else:
        selected.append(branch_id)

    await state.update_data(selected_branches=selected)
    await callback.message.edit_reply_markup(
        reply_markup=admin_kb.get_task_branches_keyboard(branches, selected)
    )


@router.callback_query(F.data == "task_branches_done", TaskStates.selecting_branches)
async def task_branches_done(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    data = await state.get_data()
    if not data.get('selected_branches'):
        await callback.answer("⚠️ Kamida bitta filial tanlang!", show_alert=True)
        return

    await state.set_state(TaskStates.selecting_shift)
    await callback.message.edit_text(
        "⏰ Smena tanlang:",
        reply_markup=admin_kb.get_shift_keyboard()
    )


@router.callback_query(F.data.startswith("task_shift_"), TaskStates.selecting_shift)
async def task_shift_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    shift = callback.data.replace("task_shift_", "")
    await state.update_data(shift=shift)
    await state.set_state(TaskStates.selecting_type)

    await callback.message.edit_text(
        "📋 Vazifa turini tanlang:",
        reply_markup=admin_kb.get_task_type_keyboard()
    )


@router.callback_query(F.data.startswith("task_type_"), TaskStates.selecting_type)
async def task_type_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    task_type = callback.data.replace("task_type_", "")
    await state.update_data(task_type=task_type)
    await state.set_state(TaskStates.selecting_result_type)

    await callback.message.edit_text(
        "📤 Natija turini tanlang:",
        reply_markup=admin_kb.get_result_type_keyboard()
    )


@router.callback_query(F.data.startswith("task_result_"), TaskStates.selecting_result_type)
async def task_result_type_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    result_type = callback.data.replace("task_result_", "")
    await state.update_data(result_type=result_type)
    await state.set_state(TaskStates.waiting_start_time)

    current_year = datetime.now().year
    await callback.message.edit_text(
        f"🕐 <b>Vazifa boshlanish vaqti</b>\n\n"
        f"Vaqtni quyidagi formatda kiriting:\n"
        f"<code>DD.MM.YYYY HH:MM</code>\n\n"
        f"Misol: <code>15.01.{current_year} 09:00</code>\n\n"
        f"Yoki faqat soat kiriting (bugungi sana uchun):\n"
        f"<code>HH:MM</code>\n"
        f"Misol: <code>09:00</code>",
        reply_markup=admin_kb.get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(TaskStates.waiting_start_time)
async def task_start_time_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    text = message.text.strip()
    start_time = None

    if ':' in text and len(text) <= 5:
        start_time = helpers.parse_time(text)
    else:
        parts = text.split()
        if len(parts) == 2:
            start_time = helpers.parse_datetime(parts[0], parts[1])
        elif len(parts) == 1 and '.' in text:
            start_time = helpers.parse_datetime(text, "00:00")

    if not start_time:
        current_year = datetime.now().year
        await message.answer(
            f"❌ Noto'g'ri format! Iltimos, quyidagi formatlardan birida kiriting:\n\n"
            f"<code>DD.MM.YYYY HH:MM</code> - To'liq format\n"
            f"Misol: <code>15.01.{current_year} 09:00</code>\n\n"
            f"<code>HH:MM</code> - Faqat soat (bugungi sana)\n"
            f"Misol: <code>09:00</code>",
            parse_mode="HTML",
            reply_markup=admin_kb.get_cancel_keyboard()
        )
        return

    await state.update_data(start_time=start_time.isoformat())
    await state.set_state(TaskStates.waiting_deadline)

    current_year = datetime.now().year
    await message.answer(
        f"⏰ <b>Deadline vaqti</b>\n\n"
        f"Vaqtni quyidagi formatda kiriting:\n"
        f"<code>DD.MM.YYYY HH:MM</code>\n\n"
        f"Misol: <code>15.01.{current_year} 18:00</code>\n\n"
        f"Yoki faqat soat kiriting (bugungi sana uchun):\n"
        f"<code>HH:MM</code>\n"
        f"Misol: <code>18:00</code>\n\n"
        f"Yoki kun oxirigacha muddatni tanlang:",
        reply_markup=admin_kb.get_skip_deadline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "task_deadline_end_of_day", TaskStates.waiting_deadline)
async def task_deadline_end_of_day(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    deadline = helpers.get_end_of_day()
    await state.update_data(deadline=deadline.isoformat())
    await state.set_state(TaskStates.confirming)
    await show_task_confirmation(callback, state)


@router.message(TaskStates.waiting_deadline)
async def task_deadline_received(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    text = message.text.strip()
    deadline = None

    if ':' in text and len(text) <= 5:
        deadline = helpers.parse_time(text)
    else:
        parts = text.split()
        if len(parts) == 2:
            deadline = helpers.parse_datetime(parts[0], parts[1])
        elif len(parts) == 1 and '.' in text:
            deadline = helpers.parse_datetime(text, "23:59")

    if not deadline:
        current_year = datetime.now().year
        await message.answer(
            f"❌ Noto'g'ri format! Iltimos, quyidagi formatlardan birida kiriting:\n\n"
            f"<code>DD.MM.YYYY HH:MM</code> - To'liq format\n"
            f"Misol: <code>15.01.{current_year} 18:00</code>\n\n"
            f"<code>HH:MM</code> - Faqat soat (bugungi sana)\n"
            f"Misol: <code>18:00</code>",
            parse_mode="HTML",
            reply_markup=admin_kb.get_skip_deadline_keyboard()
        )
        return

    await state.update_data(deadline=deadline.isoformat())
    await state.set_state(TaskStates.confirming)
    await show_task_confirmation_message(message, state)


async def show_task_confirmation(callback: CallbackQuery, state: FSMContext):
    """Callback orqali tasdiqlash oynasini ko'rsatish"""
    data = await state.get_data()

    branches = await db.get_all_branches()
    selected_branches = [b['name'] for b in branches if b['id'] in data['selected_branches']]

    start_time = datetime.fromisoformat(data['start_time'])
    deadline = datetime.fromisoformat(data['deadline'])

    text = "📋 <b>Vazifa ma'lumotlari</b>\n\n"
    text += f"📝 <b>Sarlavha:</b> {data['title']}\n"
    text += f"📄 <b>Tavsif:</b> {data['description']}\n\n"
    text += f"🏢 <b>Filiallar:</b> {', '.join(selected_branches)}\n"
    text += f"⏰ <b>Smena:</b> {helpers.get_shift_name(data['shift'])}\n"
    text += f"📋 <b>Tur:</b> {helpers.get_task_type_name(data['task_type'])}\n"
    text += f"📤 <b>Natija turi:</b> {helpers.get_result_type_name(data['result_type'])}\n\n"
    text += f"🕐 <b>Boshlanish:</b> {helpers.format_datetime(start_time)}\n"
    text += f"⏰ <b>Deadline:</b> {helpers.format_datetime(deadline)}\n"

    await callback.message.edit_text(
        text,
        reply_markup=admin_kb.get_task_confirm_keyboard(),
        parse_mode="HTML"
    )


async def show_task_confirmation_message(message: Message, state: FSMContext):
    """Message orqali tasdiqlash oynasini ko'rsatish"""
    data = await state.get_data()

    branches = await db.get_all_branches()
    selected_branches = [b['name'] for b in branches if b['id'] in data['selected_branches']]

    start_time = datetime.fromisoformat(data['start_time'])
    deadline = datetime.fromisoformat(data['deadline'])

    text = "📋 <b>Vazifa ma'lumotlari</b>\n\n"
    text += f"📝 <b>Sarlavha:</b> {data['title']}\n"
    text += f"📄 <b>Tavsif:</b> {data['description']}\n\n"
    text += f"🏢 <b>Filiallar:</b> {', '.join(selected_branches)}\n"
    text += f"⏰ <b>Smena:</b> {helpers.get_shift_name(data['shift'])}\n"
    text += f"📋 <b>Tur:</b> {helpers.get_task_type_name(data['task_type'])}\n"
    text += f"📤 <b>Natija turi:</b> {helpers.get_result_type_name(data['result_type'])}\n\n"
    text += f"🕐 <b>Boshlanish:</b> {helpers.format_datetime(start_time)}\n"
    text += f"⏰ <b>Deadline:</b> {helpers.format_datetime(deadline)}\n"

    await message.answer(
        text,
        reply_markup=admin_kb.get_task_confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "task_confirm_create")
async def task_confirm_create(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return

    current_state = await state.get_state()
    if current_state != TaskStates.confirming.state:
        await callback.answer("⚠️ Vazifa yaratish jarayoni tugagan yoki bekor qilingan!", show_alert=True)
        return

    data = await state.get_data()

    required_fields = ['title', 'description', 'task_type', 'result_type', 'shift', 'start_time', 'deadline',
                       'selected_branches']
    for field in required_fields:
        if field not in data:
            await callback.answer(f"⚠️ Ma'lumotlar to'liq emas! Qaytadan boshlang.", show_alert=True)
            await state.clear()
            return

    try:
        start_time = datetime.fromisoformat(data['start_time'])
        deadline = datetime.fromisoformat(data['deadline'])

        task_id = await db.create_task(
            title=data['title'],
            description=data['description'],
            task_type=data['task_type'],
            result_type=data['result_type'],
            shift=data['shift'],
            start_time=start_time,
            deadline=deadline,
            branch_ids=data['selected_branches']
        )

        await state.clear()

        employees = await db.get_employees_for_task(task_id)
        bot = callback.bot
        notified_count = 0

        for emp in employees:
            try:
                await bot.send_message(
                    chat_id=emp['telegram_id'],
                    text=f"📋 <b>Yangi vazifa!</b>\n\n"
                         f"📝 {data['title']}\n"
                         f"📄 {data['description']}\n\n"
                         f"🕐 Boshlanish: {helpers.format_datetime(start_time)}\n"
                         f"⏰ Deadline: {helpers.format_datetime(deadline)}\n\n"
                         f"Vazifalarni ko'rish uchun '📋 Vazifalarim' tugmasini bosing.",
                    parse_mode="HTML"
                )
                notified_count += 1
            except Exception as e:
                logger.error(f"Notification error for {emp['telegram_id']}: {e}")

        await callback.message.edit_text(
            f"✅ <b>Vazifa muvaffaqiyatli yaratildi!</b>\n\n"
            f"🆔 Vazifa ID: {task_id}\n"
            f"📬 Xabarnoma yuborildi: {notified_count} ta xodimga",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Task creation error: {e}")
        await callback.message.edit_text(
            f"❌ Vazifa yaratishda xatolik: {str(e)}\n\n"
            f"Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
        await state.clear()


# ============== XODIMLAR RO'YXATI ==============

@router.message(F.text == "👥 Xodimlar ro'yxati")
async def employees_list(message: Message):
    if not is_admin(message):
        return

    employees = await db.get_all_employees()

    if not employees:
        await message.answer("📭 Hozircha xodimlar ro'yxatdan o'tmagan.")
        return

    text = "👥 <b>Xodimlar ro'yxati</b>\n\n"

    current_branch = None
    for emp in employees:
        if emp['branch_name'] != current_branch:
            current_branch = emp['branch_name']
            text += f"\n🏢 <b>{current_branch}</b>\n"

        shift = helpers.get_shift_name(emp['shift'])
        text += f"  • {emp['first_name']} {emp['last_name']} ({shift})\n"

    await message.answer(text, parse_mode="HTML")


# ============== BEKOR QILISH ==============

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Amal bekor qilindi.")
    await callback.answer()