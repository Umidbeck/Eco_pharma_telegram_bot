"""
Employee uchun klaviaturalar
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List


def get_employee_main_menu() -> ReplyKeyboardMarkup:
    """Xodim asosiy menyu"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Vazifalarim"),
        KeyboardButton(text="👤 Profilim")
    )
    return builder.as_markup(resize_keyboard=True)


def get_register_menu() -> InlineKeyboardMarkup:
    """Ro'yxatdan o'tish menyu"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="register_start")
    )
    return builder.as_markup()


def get_branches_for_register(branches: List[dict]) -> InlineKeyboardMarkup:
    """Ro'yxatdan o'tish uchun filiallar"""
    builder = InlineKeyboardBuilder()
    for branch in branches:
        builder.row(
            InlineKeyboardButton(
                text=f"🏢 {branch['name']}",
                callback_data=f"reg_branch_{branch['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reg_cancel")
    )
    return builder.as_markup()


def get_shift_for_register() -> InlineKeyboardMarkup:
    """Ro'yxatdan o'tish uchun smena"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌅 Kunduzgi smena", callback_data="reg_shift_kunduzgi")
    )
    builder.row(
        InlineKeyboardButton(text="🌙 Kechki smena", callback_data="reg_shift_kechki")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reg_cancel")
    )
    return builder.as_markup()


def get_confirm_register() -> InlineKeyboardMarkup:
    """Ro'yxatdan o'tishni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="reg_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reg_cancel")
    )
    return builder.as_markup()


def get_profile_menu() -> InlineKeyboardMarkup:
    """Profil menyu"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="profile_edit")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Profilni o'chirish", callback_data="profile_delete")
    )
    return builder.as_markup()


def get_profile_edit_menu() -> InlineKeyboardMarkup:
    """Profil tahrirlash menyu"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Ism va familiya", callback_data="edit_name")
    )
    builder.row(
        InlineKeyboardButton(text="🏢 Filial", callback_data="edit_branch")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Smena", callback_data="edit_shift")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="profile_back")
    )
    return builder.as_markup()


def get_tasks_keyboard(tasks: List[dict]) -> InlineKeyboardMarkup:
    """Vazifalar ro'yxati"""
    builder = InlineKeyboardBuilder()
    for task in tasks:
        status = "✅" if task.get('is_completed') else "⏳"
        if task.get('is_late'):
            status = "⚠️"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {task['title'][:35]}",
                callback_data=f"emp_task_{task['id']}"
            )
        )
    if not tasks:
        builder.row(
            InlineKeyboardButton(text="📭 Hozircha vazifalar yo'q", callback_data="no_tasks")
        )
    return builder.as_markup()


def get_task_action_keyboard(task_id: int, is_completed: bool, result_type: str) -> InlineKeyboardMarkup:
    """Vazifa amallari"""
    builder = InlineKeyboardBuilder()

    if not is_completed:
        if result_type == 'matn':
            builder.row(
                InlineKeyboardButton(text="📝 Natija yuborish", callback_data=f"submit_text_{task_id}")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="📷 Rasm yuborish", callback_data=f"submit_photo_{task_id}")
            )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Vazifa bajarilgan", callback_data="already_done")
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_tasks")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_submit")
    )
    return builder.as_markup()


def get_confirm_delete_profile() -> InlineKeyboardMarkup:
    """Profilni o'chirishni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_delete_profile"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="profile_back")
    )
    return builder.as_markup()