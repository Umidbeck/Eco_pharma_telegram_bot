from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="📋 Mening vazifalarim", callback_data="my_tasks")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Admin panel", callback_data="admin_panel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_panel_kb():
    buttons = [
        [InlineKeyboardButton(text="🏢 Filial qo'shish", callback_data="add_branch")],
        [InlineKeyboardButton(text="👤 Hodim qo'shish", callback_data="add_employee")],
        [InlineKeyboardButton(text="➕ Vazifa yaratish", callback_data="create_task")],
        [InlineKeyboardButton(text="📊 Bugungi hisobot", callback_data="report")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def branches_kb(action: str):
    from db import get_conn
    buttons = []
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM branches")
        for row in c.fetchall():
            buttons.append([InlineKeyboardButton(
                text=row['name'],
                callback_data=f"{action}_branch_{row['id']}"
            )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shift_kb(action: str):
    buttons = [
        [InlineKeyboardButton(text="Kunduzgi", callback_data=f"{action}_day")],
        [InlineKeyboardButton(text="Kechki", callback_data=f"{action}_night")],
        [InlineKeyboardButton(text="Hammaga", callback_data=f"{action}_all")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def media_kb(action: str):
    buttons = [
        [InlineKeyboardButton(text="Foto", callback_data=f"{action}_photo")],
        [InlineKeyboardButton(text="Video", callback_data=f"{action}_video")],
        [InlineKeyboardButton(text="Istalgan", callback_data=f"{action}_any")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)