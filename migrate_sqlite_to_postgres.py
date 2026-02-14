#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates all data from bot.db to PostgreSQL database
"""
import asyncio
import aiosqlite
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.db_postgres import (
    Base, Branch, Employee, Task, TaskBranch,
    TaskResult, UsedPhoto, SentNotification
)
from config import DATABASE_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SQLITE_PATH = "server_data/data/bot.db"


async def migrate_data():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("🚀 Starting migration from SQLite to PostgreSQL")
    logger.info("=" * 60)

    # Create PostgreSQL engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    logger.info("📋 Creating PostgreSQL tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables created")

    # Connect to SQLite
    logger.info(f"📂 Opening SQLite database: {SQLITE_PATH}")
    async with aiosqlite.connect(SQLITE_PATH) as sqlite_db:
        sqlite_db.row_factory = aiosqlite.Row

        async with async_session_maker() as session:
            try:
                # Migrate Branches
                logger.info("\n1️⃣ Migrating branches...")
                cursor = await sqlite_db.execute("SELECT * FROM branches")
                branches = await cursor.fetchall()
                branch_map = {}
                for row in branches:
                    branch = Branch(
                        id=row['id'],
                        name=row['name'],
                        address=row['address'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    )
                    session.add(branch)
                    branch_map[row['id']] = branch
                await session.flush()
                logger.info(f"   ✅ Migrated {len(branches)} branches")

                # Migrate Employees
                logger.info("\n2️⃣ Migrating employees...")
                cursor = await sqlite_db.execute("SELECT * FROM employees")
                employees = await cursor.fetchall()
                employee_map = {}
                for row in employees:
                    employee = Employee(
                        id=row['id'],
                        telegram_id=row['telegram_id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        branch_id=row['branch_id'],
                        shift=row['shift'],
                        is_active=bool(row['is_active']),
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    )
                    session.add(employee)
                    employee_map[row['id']] = employee
                await session.flush()
                logger.info(f"   ✅ Migrated {len(employees)} employees")

                # Migrate Tasks
                logger.info("\n3️⃣ Migrating tasks...")
                cursor = await sqlite_db.execute("SELECT * FROM tasks")
                tasks = await cursor.fetchall()
                task_map = {}
                for row in tasks:
                    # Parse datetime
                    start_time_str = row['start_time']
                    deadline_str = row['deadline']
                    
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                    except:
                        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    
                    try:
                        deadline = datetime.fromisoformat(deadline_str)
                    except:
                        deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")

                    task = Task(
                        id=row['id'],
                        title=row['title'],
                        description=row['description'],
                        task_type=row['task_type'],
                        result_type=row['result_type'],
                        shift=row['shift'],
                        start_time=start_time,
                        deadline=deadline,
                        is_active=bool(row['is_active']),
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    )
                    session.add(task)
                    task_map[row['id']] = task
                await session.flush()
                logger.info(f"   ✅ Migrated {len(tasks)} tasks")

                # Migrate Task-Branch relationships
                logger.info("\n4️⃣ Migrating task-branch relationships...")
                cursor = await sqlite_db.execute("SELECT * FROM task_branches")
                task_branches = await cursor.fetchall()
                for row in task_branches:
                    task_branch = TaskBranch(
                        id=row['id'],
                        task_id=row['task_id'],
                        branch_id=row['branch_id']
                    )
                    session.add(task_branch)
                await session.flush()
                logger.info(f"   ✅ Migrated {len(task_branches)} task-branch relationships")

                # Migrate Task Results
                logger.info("\n5️⃣ Migrating task results...")
                cursor = await sqlite_db.execute("SELECT * FROM task_results")
                task_results = await cursor.fetchall()
                for row in task_results:
                    submitted_at = datetime.fromisoformat(row['submitted_at']) if row['submitted_at'] else datetime.now()
                    
                    task_result = TaskResult(
                        id=row['id'],
                        task_id=row['task_id'],
                        employee_id=row['employee_id'],
                        result_text=row['result_text'],
                        result_photo_id=row['result_photo_id'],
                        file_unique_id=row['file_unique_id'],
                        is_late=bool(row['is_late']),
                        submitted_at=submitted_at
                    )
                    session.add(task_result)
                await session.flush()
                logger.info(f"   ✅ Migrated {len(task_results)} task results")

                # Migrate Used Photos
                logger.info("\n6️⃣ Migrating used photos...")
                cursor = await sqlite_db.execute("SELECT * FROM used_photos")
                used_photos = await cursor.fetchall()
                for row in used_photos:
                    used_photo = UsedPhoto(
                        id=row['id'],
                        file_unique_id=row['file_unique_id'],
                        task_id=row['task_id'],
                        employee_id=row['employee_id'],
                        used_at=datetime.fromisoformat(row['used_at']) if row['used_at'] else datetime.now()
                    )
                    session.add(used_photo)
                await session.flush()
                logger.info(f"   ✅ Migrated {len(used_photos)} used photos")

                # Migrate Sent Notifications
                logger.info("\n7️⃣ Migrating sent notifications...")
                try:
                    cursor = await sqlite_db.execute("SELECT * FROM sent_notifications")
                    notifications = await cursor.fetchall()
                    for row in notifications:
                        notification = SentNotification(
                            id=row['id'],
                            task_id=row['task_id'],
                            employee_id=row['employee_id'],
                            notification_type=row['notification_type'],
                            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else datetime.now()
                        )
                        session.add(notification)
                    await session.flush()
                    logger.info(f"   ✅ Migrated {len(notifications)} notifications")
                except Exception as e:
                    logger.warning(f"   ⚠️ Notifications table error (may not exist): {e}")

                # Commit all changes
                await session.commit()
                logger.info("\n" + "=" * 60)
                logger.info("✅ Migration completed successfully!")
                logger.info("=" * 60)

            except Exception as e:
                await session.rollback()
                logger.error(f"\n❌ Migration failed: {e}", exc_info=True)
                raise

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_data())
        print("\n🎉 All data successfully migrated to PostgreSQL!")
        print("You can now start the bot with: python3 main.py")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        exit(1)
