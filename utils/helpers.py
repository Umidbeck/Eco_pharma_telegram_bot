"""
Yordamchi funksiyalar
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz
from config import TIMEZONE, SHIFTS, TASK_TYPES, RESULT_TYPES


def get_timezone():
    """Timezone obyektini olish"""
    return pytz.timezone(TIMEZONE)


def now():
    """Hozirgi vaqtni olish"""
    return datetime.now(get_timezone())


def parse_time(time_str: str) -> Optional[datetime]:
    """Vaqt stringini datetime ga aylantirish (format: HH:MM)"""
    try:
        tz = get_timezone()
        today = datetime.now(tz).date()
        time_parts = time_str.strip().split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        return tz.localize(datetime(today.year, today.month, today.day, hour, minute))
    except (ValueError, IndexError):
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Sana stringini datetime ga aylantirish (format: DD.MM.YYYY)"""
    try:
        tz = get_timezone()
        parts = date_str.strip().split('.')
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2]) if len(parts) > 2 else datetime.now(tz).year
        return tz.localize(datetime(year, month, day))
    except (ValueError, IndexError):
        return None


def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """Sana va vaqt stringlarini datetime ga aylantirish"""
    try:
        tz = get_timezone()
        date_parts = date_str.strip().split('.')
        time_parts = time_str.strip().split(':')

        day = int(date_parts[0])
        month = int(date_parts[1])
        year = int(date_parts[2]) if len(date_parts) > 2 else datetime.now(tz).year

        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        return tz.localize(datetime(year, month, day, hour, minute))
    except (ValueError, IndexError):
        return None


def format_datetime(dt) -> str:
    """Datetime ni chiroyli formatda ko'rsatish"""
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        try:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return dt
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt) -> str:
    """Sana formatini chiroyli ko'rsatish"""
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        try:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%d.%m.%Y")


def format_time(dt) -> str:
    """Vaqt formatini chiroyli ko'rsatish"""
    if dt is None:
        return "Noma'lum"
    if isinstance(dt, str):
        try:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%H:%M")


def get_end_of_day() -> datetime:
    """Kun oxirini olish (23:59)"""
    tz = get_timezone()
    today = datetime.now(tz)
    return tz.localize(datetime(today.year, today.month, today.day, 23, 59))


def time_until(dt) -> str:
    """Qolgan vaqtni chiroyli formatda ko'rsatish"""
    if isinstance(dt, str):
        try:
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                try:
                    dt = datetime.strptime(dt, fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = datetime.fromisoformat(dt)
        except Exception:
            return "Noma'lum"

    tz = get_timezone()
    if dt.tzinfo is None:
        dt = tz.localize(dt)

    current = datetime.now(tz)
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