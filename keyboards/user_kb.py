"""
Xodimlar uchun klaviaturalar
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List


def get_user_menu() -> ReplyKeyboardMarkup:
    """Xodim asosiy menyu"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Vazifalarim"),
        KeyboardButton(text="👤 Profilim")
    )
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def get_tasks_keyboard(tasks: List[dict]) -> InlineKeyboardMarkup:
    """Vazifalar ro'yxati"""
    builder = InlineKeyboardBuilder()

    for task in tasks:
        # Status belgilash
        if task.get('is_completed'):
            if task.get('is_late'):
                status = "⚠️"  # Kechikkan
            else:
                status = "✅"  # Bajarilgan
        else:
            status = "⏳"  # Kutilmoqda

        title = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {title}",
                callback_data=f"task_view_{task['id']}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="tasks_refresh")
    )
    return builder.as_markup()


def get_task_detail_keyboard(task_id: int, result_type: str, is_completed: bool) -> InlineKeyboardMarkup:
    """Vazifa tafsilotlari"""
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
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="my_tasks")
    )
    return builder.as_markup()


def get_cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish inline tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_submit")
    )
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Profil klaviaturasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="profile_edit")
    )
    return builder.as_markup()


def get_profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Profil tahrirlash"""
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


def get_branches_keyboard(branches: List[dict]) -> ReplyKeyboardMarkup:
    """Filiallar klaviaturasi (ro'yxatdan o'tish uchun)"""
    builder = ReplyKeyboardBuilder()
    for branch in branches:
        builder.row(KeyboardButton(text=branch['name']))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def get_shift_keyboard() -> ReplyKeyboardMarkup:
    """Smena tanlash klaviaturasi"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🌅 Kunduzgi smena"))
    builder.row(KeyboardButton(text="🌙 Kechki smena"))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def get_branch_select_keyboard(branches: List[dict]) -> InlineKeyboardMarkup:
    """Filial tanlash (inline)"""
    builder = InlineKeyboardBuilder()
    for branch in branches:
        builder.row(
            InlineKeyboardButton(
                text=f"🏢 {branch['name']}",
                callback_data=f"select_branch_{branch['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_edit")
    )
    return builder.as_markup()


def get_shift_select_keyboard() -> InlineKeyboardMarkup:
    """Smena tanlash (inline)"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌅 Kunduzgi smena", callback_data="select_shift_kunduzgi")
    )
    builder.row(
        InlineKeyboardButton(text="🌙 Kechki smena", callback_data="select_shift_kechki")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_edit")
    )
    return builder.as_markup()