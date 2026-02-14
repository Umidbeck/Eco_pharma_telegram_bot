"""
Admin uchun klaviaturalar
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Admin asosiy menyu"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🏢 Filiallar"),
        KeyboardButton(text="📊 Statistika")
    )
    builder.row(
        KeyboardButton(text="📋 Vazifa yaratish"),
        KeyboardButton(text="📝 Vazifalar ro'yxati")
    )
    builder.row(
        KeyboardButton(text="📈 Hisobotlar"),
        KeyboardButton(text="👥 Xodimlar ro'yxati")
    )
    return builder.as_markup(resize_keyboard=True)


def get_branches_menu() -> InlineKeyboardMarkup:
    """Filiallar menyu"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Yangi filial", callback_data="branch_add")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Filiallar ro'yxati", callback_data="branch_list")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()


def get_branches_list(branches: List[dict]) -> InlineKeyboardMarkup:
    """Filiallar ro'yxati"""
    builder = InlineKeyboardBuilder()
    for branch in branches:
        builder.row(
            InlineKeyboardButton(
                text=f"🏢 {branch['name']}",
                callback_data=f"branch_view_{branch['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="branches_menu")
    )
    return builder.as_markup()


def get_branch_actions(branch_id: int) -> InlineKeyboardMarkup:
    """Filial amallari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"branch_edit_{branch_id}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"branch_delete_{branch_id}")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Xodimlar", callback_data=f"branch_employees_{branch_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="branch_list")
    )
    return builder.as_markup()


def get_confirm_delete(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"{item_type}_confirm_delete_{item_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{item_type}_list")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_task_branches_keyboard(branches: List[dict], selected_ids: List[int] = None) -> InlineKeyboardMarkup:
    """Vazifa uchun filiallarni tanlash"""
    if selected_ids is None:
        selected_ids = []

    builder = InlineKeyboardBuilder()

    # "Barcha filiallar" tugmasi
    all_selected = len(selected_ids) == len(branches) and len(branches) > 0
    all_text = "✅ Barcha filiallar" if all_selected else "⬜️ Barcha filiallar"
    builder.row(
        InlineKeyboardButton(text=all_text, callback_data="task_branch_all")
    )

    # Har bir filial
    for branch in branches:
        is_selected = branch['id'] in selected_ids
        text = f"✅ {branch['name']}" if is_selected else f"⬜️ {branch['name']}"
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"task_branch_{branch['id']}")
        )

    builder.row(
        InlineKeyboardButton(text="✔️ Davom etish", callback_data="task_branches_done")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_shift_keyboard() -> InlineKeyboardMarkup:
    """Smena tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌅 Kunduzgi", callback_data="task_shift_kunduzgi")
    )
    builder.row(
        InlineKeyboardButton(text="🌙 Kechki", callback_data="task_shift_kechki")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Hammasi", callback_data="task_shift_hammasi")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_task_type_keyboard() -> InlineKeyboardMarkup:
    """Vazifa turi tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔹 Bir martalik", callback_data="task_type_bir_martalik")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Har kunlik", callback_data="task_type_har_kunlik")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_result_type_keyboard() -> InlineKeyboardMarkup:
    """Natija turi tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Matn", callback_data="task_result_matn")
    )
    builder.row(
        InlineKeyboardButton(text="📷 Rasm", callback_data="task_result_rasm")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_skip_deadline_keyboard() -> InlineKeyboardMarkup:
    """Deadline o'tkazib yuborish"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Kun oxirigacha", callback_data="task_deadline_end_of_day")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_task_confirm_keyboard() -> InlineKeyboardMarkup:
    """Vazifani tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yaratish", callback_data="task_confirm_create"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    )
    return builder.as_markup()


def get_reports_menu() -> InlineKeyboardMarkup:
    """Hisobotlar menyu"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Faol vazifalar", callback_data="report_active_tasks")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Vazifa statistikasi", callback_data="report_task_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()


def get_active_tasks_keyboard(tasks: List[dict]) -> InlineKeyboardMarkup:
    """Faol vazifalar ro'yxati"""
    builder = InlineKeyboardBuilder()
    for task in tasks:
        title = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
        builder.row(
            InlineKeyboardButton(
                text=f"📋 {title}",
                callback_data=f"report_task_{task['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="reports_menu")
    )
    return builder.as_markup()


def get_task_report_options_keyboard(
    task_id: int,
) -> InlineKeyboardMarkup:
    """Vazifa hisoboti - bajarganlar/bajarmaganlar tanlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Bajarganlar",
            callback_data=f"report_submitted_{task_id}",
        ),
        InlineKeyboardButton(
            text="❌ Bajarmaganlar",
            callback_data=f"report_notdone_{task_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="report_active_tasks",
        )
    )
    return builder.as_markup()


def get_task_report_back_keyboard(
    task_id: int | None = None,
) -> InlineKeyboardMarkup:
    """Vazifa hisobotidan orqaga qaytish"""
    builder = InlineKeyboardBuilder()
    if task_id is not None:
        builder.row(
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data=f"report_task_{task_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data="back_to_reports",
            )
        )
    return builder.as_markup()


# ============== VAZIFALAR BOSHQARUVI ==============

def get_tasks_list_keyboard(tasks: List[dict]) -> InlineKeyboardMarkup:
    """Vazifalar ro'yxati (admin uchun boshqarish)"""
    builder = InlineKeyboardBuilder()
    for task in tasks:
        title = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
        builder.row(
            InlineKeyboardButton(
                text=f"📋 {title}",
                callback_data=f"task_manage_{task['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_back")
    )
    return builder.as_markup()


def get_task_manage_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Vazifa boshqaruv tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data=f"task_stats_{task_id}"),
        InlineKeyboardButton(text="📋 Natijalar", callback_data=f"task_results_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"task_edit_{task_id}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"task_delete_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="tasks_list_back")
    )
    return builder.as_markup()


def get_task_results_keyboard(task_id: int, results: List[dict]) -> InlineKeyboardMarkup:
    """Vazifa natijalari ro'yxati"""
    builder = InlineKeyboardBuilder()
    for result in results:
        name = f"{result.get('first_name', '')} {result.get('last_name', '')}"
        status = "⚠️" if result.get('is_late') else "✅"
        result_type = "📷" if result.get('result_photo_id') else "📝"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {result_type} {name[:25]}",
                callback_data=f"view_result_{result['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"task_manage_{task_id}")
    )
    return builder.as_markup()


def get_result_view_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Natija ko'rish tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"task_results_{task_id}")
    )
    return builder.as_markup()


def get_confirm_task_delete(task_id: int) -> InlineKeyboardMarkup:
    """Vazifa o'chirishni tasdiqlash"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_task_delete_{task_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"task_manage_{task_id}")
    )
    return builder.as_markup()


def get_task_edit_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Vazifa tahrirlash menyusi"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Sarlavha", callback_data=f"edit_task_title_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📄 Tavsif", callback_data=f"edit_task_desc_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🕐 Boshlanish", callback_data=f"edit_task_start_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Deadline", callback_data=f"edit_task_deadline_{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"task_manage_{task_id}")
    )
    return builder.as_markup()