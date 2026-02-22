"""
Scheduler - Vaqtli vazifalar uchun
"""
import asyncio
from datetime import datetime, timedelta
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from config import TIMEZONE, ADMIN_IDS
from database import db
from utils import helpers

logger = logging.getLogger(__name__)

# Global scheduler reference
_scheduler = None


async def check_task_notifications(bot):
    """Vazifa bildirishnomalarini tekshirish"""
    try:
        tasks = await db.get_active_tasks()
        tz = pytz.timezone(TIMEZONE)
        # NAIVE Tashkent vaqti - DB dagi vaqtlar bilan taqqoslash uchun
        now = datetime.now(tz).replace(tzinfo=None)

        for task in tasks:
            try:
                start_time_str = task['start_time']
                deadline_str = task['deadline']

                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        start_time = datetime.strptime(start_time_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    start_time = datetime.fromisoformat(start_time_str)

                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    deadline = datetime.fromisoformat(deadline_str)

                # Naive qilish (agar tz-aware bo'lsa)
                if start_time.tzinfo is not None:
                    start_time = start_time.astimezone(tz).replace(tzinfo=None)
                if deadline.tzinfo is not None:
                    deadline = deadline.astimezone(tz).replace(tzinfo=None)
                    
                # Har kunlik vazifa uchun sanani bugungi kunga moslash
                if task.get('task_type') == 'har_kunlik':
                    if start_time.date() < now.date():
                        start_time = start_time.replace(year=now.year, month=now.month, day=now.day)
                    if deadline.date() < now.date() or deadline <= start_time:
                        deadline = deadline.replace(year=now.year, month=now.month, day=now.day)
                    if deadline <= start_time:
                        deadline += timedelta(days=1)

                employees = await db.get_employees_for_task(task['id'])

                # Filial bo'yicha xodimlarni guruhlash
                branch_employees = {}
                for emp in employees:
                    bid = emp.get('branch_id') or emp.get('branch_name', 'unknown')
                    if bid not in branch_employees:
                        branch_employees[bid] = []
                    branch_employees[bid].append(emp)

                # Har bir filial uchun bajarilganligini tekshirish
                branch_has_completion = {}
                for bid in branch_employees:
                    branch_has_completion[bid] = await db.has_branch_completion(
                        task['id'], bid, task['shift']
                    )

                # Vazifa boshlanganda ogohlantirish (faqat 1 marta)
                time_diff = abs((start_time - now).total_seconds())
                if time_diff <= 90:  # 90 soniya oraliqda tekshirish
                    for emp in employees:
                        bid = emp.get('branch_id') or emp.get('branch_name', 'unknown')
                        # Agar filialda birorta xodim bajargan bo'lsa, xabar yubormasin
                        if branch_has_completion.get(bid, False):
                            continue
                        result = await db.get_task_result(task['id'], emp['id'])
                        if not result:
                            # Avval yuborilganligini tekshirish
                            already_sent = await db.check_notification_sent(
                                task['id'], emp['id'], 'task_started'
                            )
                            if not already_sent:
                                try:
                                    await bot.send_message(
                                        chat_id=emp['telegram_id'],
                                        text=f"🔔 <b>Vazifa boshlandi!</b>\n\n"
                                             f"📋 {task['title']}\n"
                                             f"⏰ Deadline: {helpers.format_datetime(deadline)}\n\n"
                                             f"Vazifani bajarish uchun '📋 Vazifalarim' tugmasini bosing.",
                                        parse_mode="HTML"
                                    )
                                    # Yuborilganligini belgilash
                                    await db.mark_notification_sent(
                                        task['id'], emp['id'], 'task_started'
                                    )
                                except Exception as e:
                                    logger.error(f"Notification error: {e}")

                # 30 daqiqa qoldi ogohlantirish (faqat 1 marta)
                time_to_deadline = (deadline - now).total_seconds()
                if 1680 <= time_to_deadline <= 1920:  # 28-32 daqiqa oralig'ida
                    for emp in employees:
                        bid = emp.get('branch_id') or emp.get('branch_name', 'unknown')
                        # Agar filialda birorta xodim bajargan bo'lsa, xabar yubormasin
                        if branch_has_completion.get(bid, False):
                            continue
                        result = await db.get_task_result(task['id'], emp['id'])
                        if not result:
                            # Avval yuborilganligini tekshirish
                            already_sent = await db.check_notification_sent(
                                task['id'], emp['id'], 'warning_30min'
                            )
                            if not already_sent:
                                try:
                                    await bot.send_message(
                                        chat_id=emp['telegram_id'],
                                        text=f"⚠️ <b>Ogohlantirish!</b>\n\n"
                                             f"📋 {task['title']}\n"
                                             f"⏰ Deadline tugashiga 30 daqiqa qoldi!\n\n"
                                             f"Vazifani bajarish uchun '📋 Vazifalarim' tugmasini bosing.",
                                        parse_mode="HTML"
                                    )
                                    # Yuborilganligini belgilash
                                    await db.mark_notification_sent(
                                        task['id'], emp['id'], 'warning_30min'
                                    )
                                except Exception as e:
                                    logger.error(f"Notification error: {e}")

                # Deadline tugadi (faqat 1 marta)
                if -90 <= time_to_deadline <= 0:
                    # Admin uchun hisobotni faqat 1 marta yuborish
                    admin_notified = await db.check_notification_sent(
                        task['id'], 0, 'deadline_report'  # employee_id=0 admin uchun
                    )

                    if not admin_notified:
                        # Filial bo'yicha xodimlarni guruhlash
                        stats = await db.get_task_statistics(task['id'])

                        # Faqat vazifa yubormaganlarni ko'rsatish
                        report_text = f"📊 <b>Vazifa muddati yakunlandi!</b>\n\n"
                        report_text += f"📋 {task['title']}\n"
                        report_text += f"⏰ Deadline: {helpers.format_datetime(deadline)}\n\n"

                        total_not_completed = 0
                        branches_with_incomplete = []

                        for branch_stat in stats.get('branches', []):
                            # Filialda birorta xodim bajargan bo'lsa, bu filialni o'tkazib yuborish
                            has_completed = len(branch_stat['completed']) > 0 or len(branch_stat['late']) > 0
                            if has_completed:
                                continue

                            not_completed = branch_stat['not_completed']
                            if not_completed:
                                branches_with_incomplete.append(branch_stat)
                                total_not_completed += len(not_completed)

                        if branches_with_incomplete:
                            report_text += "<b>❌ Vazifa yubormaganlar:</b>\n"
                            for branch_stat in branches_with_incomplete:
                                report_text += f"\n🏢 <b>{branch_stat['name']}</b>\n"
                                for emp_info in branch_stat['not_completed']:
                                    report_text += f"  • {emp_info['name']}\n"

                            report_text += f"\n<b>Jami yubormaganlar: {total_not_completed} ta</b>"
                        else:
                            report_text += "✅ <b>Barcha filiallardan vazifa bajarilgan!</b>"

                        for admin_id in ADMIN_IDS:
                            try:
                                await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="HTML")
                            except Exception as e:
                                logger.error(f"Admin notification error: {e}")

                        # Admin hisoboti yuborilganligini belgilash
                        await db.mark_notification_sent(task['id'], 0, 'deadline_report')

                    # Filial bo'yicha guruhlangan xodimlar ro'yxatini olish
                    stats = await db.get_task_statistics(task['id'])

                    # Filial bo'yicha: agar bitta xodim vazifa bajargan bo'lsa,
                    # o'sha filialdagi boshqalarga xabar yuborilmasin
                    for branch_stat in stats.get('branches', []):
                        # Agar filialdan hech bo'lmaganda 1 ta xodim vazifa bajargan bo'lsa
                        has_completed_in_branch = len(branch_stat['completed']) > 0 or len(branch_stat['late']) > 0

                        if not has_completed_in_branch:
                            # Faqat hech kim vazifa bajarmagan filiallar uchun xabar yuborish
                            for emp_info in branch_stat['not_completed']:
                                emp_id = emp_info['id']
                                telegram_id = emp_info['telegram_id']

                                # Avval yuborilganligini tekshirish
                                already_sent = await db.check_notification_sent(
                                    task['id'], emp_id, 'deadline_ended'
                                )
                                if not already_sent:
                                    try:
                                        await bot.send_message(
                                            chat_id=telegram_id,
                                            text=f"❌ <b>Vazifa muddati tugadi!</b>\n\n"
                                                 f"📋 {task['title']}\n\n"
                                                 f"Siz bu vazifani bajarmadingiz.\n"
                                                 f"Endi yuborilgan natijalar 'Kechiktirilgan' deb belgilanadi.",
                                            parse_mode="HTML"
                                        )
                                        # Yuborilganligini belgilash
                                        await db.mark_notification_sent(
                                            task['id'], emp_id, 'deadline_ended'
                                        )
                                    except Exception as e:
                                        logger.error(f"Employee notification error: {e}")

                    if task['task_type'] == 'bir_martalik':
                        await db.deactivate_task(task['id'])

            except Exception as e:
                logger.error(f"Task notification error for task {task['id']}: {e}")

    except Exception as e:
        logger.error(f"Notification error: {e}")


async def recreate_daily_tasks(bot):
    """Har kunlik vazifalarni qayta yaratish"""
    try:
        daily_tasks = await db.get_daily_tasks()
        tz = pytz.timezone(TIMEZONE)
        # NAIVE Tashkent vaqti
        now = datetime.now(tz).replace(tzinfo=None)

        for task in daily_tasks:
            try:
                # Eski vazifaning bildirishnomalarini tozalash
                await db.clear_task_notifications(task['id'])
                await db.deactivate_task(task['id'])

                start_time_str = task['start_time']
                deadline_str = task['deadline']

                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        start_time = datetime.strptime(start_time_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    start_time = datetime.fromisoformat(start_time_str)

                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                    try:
                        deadline = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    deadline = datetime.fromisoformat(deadline_str)

                # NAIVE datetime - Tashkent mahalliy vaqti
                new_start = datetime(now.year, now.month, now.day, start_time.hour, start_time.minute)
                new_deadline = datetime(now.year, now.month, now.day, deadline.hour, deadline.minute)

                if new_deadline <= new_start:
                    new_deadline += timedelta(days=1)

                branches = await db.get_task_branches(task['id'])
                branch_ids = [b['id'] for b in branches]

                if branch_ids:
                    new_task_id = await db.create_task(
                        title=task['title'],
                        description=task['description'],
                        task_type='har_kunlik',
                        result_type=task['result_type'],
                        shift=task['shift'],
                        start_time=new_start,
                        deadline=new_deadline,
                        branch_ids=branch_ids
                    )

                    employees = await db.get_employees_for_task(new_task_id)
                    for emp in employees:
                        try:
                            await bot.send_message(
                                chat_id=emp['telegram_id'],
                                text=f"📋 <b>Kunlik vazifa!</b>\n\n"
                                     f"📝 {task['title']}\n"
                                     f"📄 {task['description']}\n\n"
                                     f"🕐 Boshlanish: {helpers.format_datetime(new_start)}\n"
                                     f"⏰ Deadline: {helpers.format_datetime(new_deadline)}\n\n"
                                     f"Vazifalarni ko'rish uchun '📋 Vazifalarim' tugmasini bosing.",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Daily task notification error: {e}")

            except Exception as e:
                logger.error(f"Daily task recreate error for task {task['id']}: {e}")

    except Exception as e:
        logger.error(f"Daily tasks error: {e}")


async def reset_daily_results(bot):
    """
    Har kuni soat 01:00 da barcha natijalarni tozalash.
    Xodimlarga HECH QANDAY xabar yuborilmaydi - faqat ma'lumotlar tozalanadi.
    
    MUHIM: Ishlatilgan rasmlar (used_photos) TOZALANMAYDI!
    Bu xodimlar bir marta yuborgan rasmni qayta yubora olmasligi uchun ABADIY saqlanadi.
    """
    try:
        logger.info("🔄 Kunlik natijalarni qayta tiklash boshlandi...")
        
        # Barcha natijalarni tozalash (RASMLAR TOZALANMAYDI!)
        await db.clear_all_task_results()
        await db.clear_all_notifications()
        # await db.clear_all_used_photos()  # BU O'CHIRILDI - rasmlar abadiy saqlanadi!
        
        logger.info("✅ Kunlik natijalar muvaffaqiyatli qayta tiklandi!")
        
        # Faqat adminlarga xabar yuborish
        for admin_id in ADMIN_IDS:
            try:
                tz = pytz.timezone(TIMEZONE)
                now = datetime.now(tz)
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"🔄 <b>Kunlik natijalar qayta tiklandi</b>\n\n"
                         f"⏰ Vaqt: {helpers.format_datetime(now)}\n"
                         f"✅ Barcha vazifa natijalari 0 ga qaytarildi\n"
                         f"✅ Bildirishnomalar tozalandi\n"
                         f"📸 Ishlatilgan rasmlar ABADIY saqlanadi",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Admin notification error: {e}")
                
    except Exception as e:
        logger.error(f"❌ Kunlik natijalarni qayta tiklashda xatolik: {e}")


async def setup_scheduler(scheduler: AsyncIOScheduler, bot):
    """Schedulerni sozlash"""
    global _scheduler
    _scheduler = scheduler

    scheduler.add_job(
        check_task_notifications,
        IntervalTrigger(minutes=1),
        args=[bot],
        id='check_notifications',
        replace_existing=True
    )

    # Soat 01:20 da kunlik natijalarni 0 ga qaytarish
    tz = pytz.timezone(TIMEZONE)
    scheduler.add_job(
        reset_daily_results,
        CronTrigger(hour=1, minute=20, timezone=tz),  # 01:20 ga o'zgartirildi
        args=[bot],
        id='reset_daily_results',
        replace_existing=True
    )

    logger.info("✅ Scheduler setup completed")
    logger.info("📋 Scheduled jobs:")
    logger.info("   • check_notifications: har 1 daqiqada")
    logger.info("   • reset_daily_results: har kuni soat 01:20 da")


def stop_scheduler():
    """Schedulerni to'xtatish"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")