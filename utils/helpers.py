"""
Yordamchi funksiyalar

MUHIM: Barcha vaqtlar NAIVE datetime sifatida saqlanadi (timezone info'siz).
Barcha vaqtlar Tashkent mahalliy vaqtini ifodalaydi.
Bu asyncpg/PostgreSQL ning tz-aware datetime ni UTC ga o'girish muammosini hal qiladi.
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz
from config import TIMEZONE, SHIFTS, TASK_TYPES, RESULT_TYPES


def get_timezone():
    """Timezone obyektini olish"""
    return pytz.timezone(TIMEZONE)


def now() -> datetime:
    """Hozirgi Tashkent vaqtini olish (NAIVE - timezone info'siz).
    Bu DB saqlash va taqqoslash uchun xavfsiz.
    """
    tz = get_timezone()
    tashkent_now = datetime.now(tz)
    # Naive datetime qaytarish (timezone info'siz)
    return tashkent_now.replace(tzinfo=None)


def now_aware() -> datetime:
    """Hozirgi Tashkent vaqtini olish (TZ-AWARE).
    Faqat scheduler va tz-aware taqqoslash uchun.
    """
    return datetime.now(get_timezone())


def parse_time(time_str: str) -> Optional[datetime]:
    """Vaqt stringini datetime ga aylantirish (format: HH:MM).
    NAIVE datetime qaytaradi (Tashkent mahalliy vaqti).
    """
    try:
        tz = get_timezone()
        today = datetime.now(tz).date()
        time_parts = time_str.strip().split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        # Validatsiya
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        # NAIVE datetime qaytarish - timezone info'siz
        return datetime(today.year, today.month, today.day, hour, minute)
    except (ValueError, IndexError):
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Sana stringini datetime ga aylantirish (format: DD.MM.YYYY).
    NAIVE datetime qaytaradi.
    """
    try:
        tz = get_timezone()
        parts = date_str.strip().split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2]) if len(parts) > 2 else datetime.now(tz).year
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """Sana va vaqt stringlarini datetime ga aylantirish.
    NAIVE datetime qaytaradi (Tashkent mahalliy vaqti).
    """
    try:
        tz = get_timezone()
        date_parts = date_str.strip().split('.')
        time_parts = time_str.strip().split(':')

        day = int(date_parts[0])
        month = int(date_parts[1])
        year = int(date_parts[2]) if len(date_parts) > 2 else datetime.now(tz).year

        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        # Validatsiya
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        # NAIVE datetime qaytarish
        return datetime(year, month, day, hour, minute)
    except (ValueError, IndexError):
        return None


def to_naive(dt) -> Optional[datetime]:
    """Har qanday datetime ni naive Tashkent vaqtiga o'girish.
    Agar tz-aware bo'lsa, Tashkent vaqtiga o'girib, tzinfo olib tashlanadi.
    Agar naive bo'lsa, o'zgartirmasdan qaytaradi.
    Agar string bo'lsa, parse qilib naive qaytaradi.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = _parse_datetime_string(dt)
        if dt is None:
            return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        # TZ-aware: Tashkent vaqtiga o'girib, tzinfo olib tashlash
        tz = get_timezone()
        dt = dt.astimezone(tz)
        return dt.replace(tzinfo=None)
    return dt


def _parse_datetime_string(dt_str: str) -> Optional[datetime]:
    """Datetime stringini parse qilish (ichki yordamchi funksiya)"""
    if not isinstance(dt_str, str):
        return dt_str
    try:
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                     "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        # ISO format bilan sinash (timezone bilan ham)
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None


def format_datetime(dt) -> str:
    """Datetime ni chiroyli formatda ko'rsatish.
    Agar tz-aware bo'lsa, avval Tashkent vaqtiga o'giradi.
    """
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        parsed = _parse_datetime_string(dt)
        if parsed is None:
            return dt
        dt = parsed
    # Agar tz-aware bo'lsa, Tashkent vaqtiga o'girish
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        tz = get_timezone()
        dt = dt.astimezone(tz)
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt) -> str:
    """Sana formatini chiroyli ko'rsatish"""
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        parsed = _parse_datetime_string(dt)
        if parsed is None:
            return dt
        dt = parsed
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        tz = get_timezone()
        dt = dt.astimezone(tz)
    return dt.strftime("%d.%m.%Y")


def format_time(dt) -> str:
    """Vaqt formatini chiroyli ko'rsatish"""
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        parsed = _parse_datetime_string(dt)
        if parsed is None:
            return dt
        dt = parsed
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        tz = get_timezone()
        dt = dt.astimezone(tz)
    return dt.strftime("%H:%M")


def get_end_of_day() -> datetime:
    """Kun oxirini olish (23:59) - NAIVE Tashkent vaqti"""
    tz = get_timezone()
    today = datetime.now(tz)
    return datetime(today.year, today.month, today.day, 23, 59)


def time_until(dt) -> str:
    """Qolgan vaqtni chiroyli formatda ko'rsatish"""
    if isinstance(dt, str):
        dt = _parse_datetime_string(dt)
        if dt is None:
            return "Noma'lum"

    # Naive datetime bilan ishlash
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        dt = to_naive(dt)

    current = now()  # Naive Tashkent vaqti
    diff = dt - current

    if diff.total_seconds() <= 0:
        return "muddati o'tgan"

    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} kun")
    if hours > 0:
        parts.append(f"{hours} soat")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes} daqiqa")

    return " ".join(parts) if parts else "1 daqiqadan kam"


def get_shift_name(shift: str) -> str:
    """Smena nomini olish"""
    shifts = {
        "kunduzgi": "🌅 Kunduzgi",
        "kechki": "🌙 Kechki",
        "hammasi": "📋 Barcha smenalar"
    }
    return shifts.get(shift, shift)


def get_task_type_name(task_type: str) -> str:
    """Vazifa turi nomini olish"""
    types = {
        "bir_martalik": "🔹 Bir martalik",
        "har_kunlik": "🔄 Har kunlik"
    }
    return types.get(task_type, task_type)


def get_result_type_name(result_type: str) -> str:
    """Natija turi nomini olish"""
    types = {
        "matn": "📝 Matn",
        "rasm": "📷 Rasm"
    }
    return types.get(result_type, result_type)


def get_position_emoji(position: int) -> str:
    """Pozitsiya uchun emoji olish"""
    emojis = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }
    return emojis.get(position, "🏅")