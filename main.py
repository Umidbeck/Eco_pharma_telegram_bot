"""
============================================================
Eco Pharm Telegram Bot - Main Entry Point
Linux Server uchun optimallashtirilgan - 24/7 ishlash
============================================================
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from config import BOT_TOKEN, ADMIN_IDS, TIMEZONE, LOG_FILE
from database import init_db, close_db
from handlers import registration, admin_router, admin_tasks, user, employee_router
from utils.scheduler import setup_scheduler


# ============================================================
# LOGGING SETUP
# ============================================================
def setup_logging() -> logging.Logger:
    """Logging ni sozlash - fayl va konsolga"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Eski handlerlarni tozalash
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler
    try:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Log faylni yaratib bo'lmadi: {e}")

    # External kutubxonalar uchun log darajasini kamaytirish
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================
# GLOBAL VARIABLES
# ============================================================
bot: Bot = None
dp: Dispatcher = None
scheduler: AsyncIOScheduler = None
shutdown_event = asyncio.Event()


# ============================================================
# STARTUP
# ============================================================
async def on_startup():
    """Bot ishga tushganda"""
    logger.info("=" * 60)
    logger.info("🚀 Eco Pharm Bot ishga tushmoqda...")
    logger.info(f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🌍 Timezone: {TIMEZONE}")
    logger.info(f"👨‍💼 Admin IDs: {ADMIN_IDS}")

    # Ma'lumotlar bazasini initsializatsiya
    await init_db()
    logger.info("✅ Ma'lumotlar bazasi tayyor")


# ============================================================
# SHUTDOWN
# ============================================================
async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("🛑 Bot to'xtatilmoqda...")

    # Scheduler ni to'xtatish
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("✅ Scheduler to'xtatildi")

    # Database ni yopish
    await close_db()
    logger.info("✅ Database ulanishi yopildi")

    # Bot session ni yopish
    global bot
    if bot:
        await bot.session.close()
        logger.info("✅ Bot session yopildi")

    logger.info("❌ Bot to'xtatildi")
    logger.info("=" * 60)


# ============================================================
# SIGNAL HANDLERS
# ============================================================
def handle_signal(sig, frame):
    """Signal handler - SIGINT/SIGTERM uchun"""
    signal_name = signal.Signals(sig).name
    logger.info(f"📡 Signal qabul qilindi: {signal_name}")
    shutdown_event.set()


# ============================================================
# MAIN
# ============================================================
async def main():
    """Botni ishga tushirish"""
    global bot, dp, scheduler

    try:
        # Startup
        await on_startup()

        # Bot yaratish
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode='HTML')
        )

        # Dispatcher yaratish
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Scheduler yaratish va sozlash
        scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
        await setup_scheduler(scheduler, bot)
        scheduler.start()
        logger.info("✅ Scheduler ishga tushdi")

        # Handlerlarni ro'yxatdan o'tkazish (tartib muhim!)
        dp.include_router(registration.router)      # Ro'yxatdan o'tish
        dp.include_router(admin_router)             # Admin handlers
        dp.include_router(admin_tasks.router)       # Admin tasks
        dp.include_router(user.router)              # User handlers
        dp.include_router(employee_router)          # Employee handlers

        logger.info("✅ Barcha handlerlar ro'yxatdan o'tdi")

        # Adminlarga xabar yuborish
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "🟢 <b>Bot ishga tushdi!</b>\n\n"
                        f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"🖥 Platform: Linux Server\n"
                        f"🐳 Docker: Active"
                    )
                )
            except Exception as e:
                logger.warning(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")

        # Polling boshlash
        logger.info("🤖 Bot polling boshlanmoqda...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=False
        )

    except asyncio.CancelledError:
        logger.info("Bot polling bekor qilindi")
    except Exception as e:
        logger.error(f"Bot ishga tushirishda xatolik: {e}", exc_info=True)
        raise
    finally:
        await on_shutdown()


# ============================================================
# RUN BOT
# ============================================================
def run_bot():
    """Botni xavfsiz ishga tushirish"""
    # Signal handlerlarni o'rnatish
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    retry_count = 0
    max_retries = 5
    retry_delay = 10

    while retry_count < max_retries:
        try:
            logger.info(f"🔄 Bot ishga tushirilmoqda (urinish {retry_count + 1}/{max_retries})...")
            asyncio.run(main())
            break  # Normal exit

        except KeyboardInterrupt:
            logger.info("❌ Bot foydalanuvchi tomonidan to'xtatildi")
            break

        except SystemExit:
            logger.info("❌ System exit")
            break

        except Exception as e:
            retry_count += 1
            logger.error(f"Bot xatolik bilan to'xtadi: {e}", exc_info=True)

            if retry_count < max_retries:
                logger.info(f"⏳ {retry_delay} soniyadan so'ng qayta urinish...")
                import time
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # Max 60 soniya
            else:
                logger.error(f"❌ Maksimal urinishlar soni ({max_retries}) oshib ketdi")
                sys.exit(1)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    run_bot()