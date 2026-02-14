"""
============================================================
Eco Pharm Telegram Bot - Configuration
Linux Server uchun optimallashtirilgan
============================================================
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# ============================================================
# BOT TOKEN
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ XATOLIK: BOT_TOKEN environment variable topilmadi!")
    print("Iltimos, .env faylida BOT_TOKEN ni sozlang.")
    sys.exit(1)

# ============================================================
# ADMIN IDS
# ============================================================
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []

for x in admin_ids_str.split(","):
    x = x.strip()
    if x:
        try:
            ADMIN_IDS.append(int(x))
        except ValueError:
            print(f"⚠️ Ogohlantirish: Noto'g'ri admin ID '{x}' e'tiborsiz qoldirildi")

if not ADMIN_IDS:
    print("⚠️ Ogohlantirish: Admin ID'lar sozlanmagan!")

# ============================================================
# TIMEZONE
# ============================================================
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

# ============================================================
# DATABASE
# ============================================================
# Database type: sqlite or postgresql
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")

# SQLite (legacy - migration only)
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/bot.db")

# PostgreSQL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "eco_pharm_bot")
POSTGRES_USER = os.getenv("POSTGRES_USER", "eco_pharm")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "eco_pharm_2024")

# PostgreSQL connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Database papkasini yaratish (SQLite uchun)
if DATABASE_TYPE == "sqlite":
    try:
        db_dir = Path(DATABASE_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"⚠️ Ogohlantirish: Database papkasini yaratib bo'lmadi: {db_dir}")
    except Exception as e:
        print(f"⚠️ Ogohlantirish: Database papkasi xatoligi: {e}")

# ============================================================
# LOGGING
# ============================================================
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/bot.log")

# Log papkasini yaratish
try:
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print(f"⚠️ Ogohlantirish: Log papkasini yaratib bo'lmadi: {log_dir}")
except Exception as e:
    print(f"⚠️ Ogohlantirish: Log papkasi xatoligi: {e}")

# ============================================================
# CONSTANTS - Smenalar
# ============================================================
SHIFTS = {
    "kunduzgi": "🌅 Kunduzgi smena",
    "kechki": "🌙 Kechki smena",
    "hammasi": "📋 Barcha smenalar"
}

# ============================================================
# CONSTANTS - Vazifa turlari
# ============================================================
TASK_TYPES = {
    "bir_martalik": "🔹 Bir martalik",
    "har_kunlik": "🔄 Har kunlik"
}

# ============================================================
# CONSTANTS - Natija turlari
# ============================================================
RESULT_TYPES = {
    "matn": "📝 Matn",
    "rasm": "📷 Rasm"
}

# ============================================================
# DEBUG MODE
# ============================================================
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# ============================================================
# Konfiguratsiay xulosasi (faqat debug mode'da)
# ============================================================
if DEBUG:
    print("=" * 50)
    print("🔧 Konfiguratsiya:")
    print(f"   • Bot Token: {'✅ Sozlangan' if BOT_TOKEN else '❌ Yoq'}")
    print(f"   • Admin IDs: {ADMIN_IDS}")
    print(f"   • Timezone: {TIMEZONE}")
    print(f"   • Database: {DATABASE_PATH}")
    print(f"   • Log File: {LOG_FILE}")
    print("=" * 50)