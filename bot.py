import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import db
from handlers import admin_router, employee_router
from utils.scheduler import setup_scheduler, stop_scheduler

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot va Dispatcher yaratish
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup():
    """Bot ishga tushganda"""
    logger.info("Bot ishga tushmoqda...")

    # Ma'lumotlar bazasini yaratish
    await db.init_db()
    logger.info("Ma'lumotlar bazasi tayyor")

    # Schedulerni yaratish va ishga tushirish
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    await setup_scheduler(scheduler, bot)
    scheduler.start()
    logger.info("Scheduler ishga tushdi")

    logger.info("Bot muvaffaqiyatli ishga tushdi!")


async def on_shutdown():
    """Bot to'xtashida"""
    logger.info("Bot to'xtamoqda...")
    stop_scheduler()
    await bot.session.close()
    logger.info("Bot to'xtadi")


async def main():
    """Asosiy funksiya"""
    # Routerlarni ro'yxatdan o'tkazish
    dp.include_router(admin_router)
    dp.include_router(employee_router)

    # Startup va shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Botni ishga tushirish
    try:
        logger.info("Bot polling boshlanmoqda...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())