#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates all data from bot.db to PostgreSQL database

Uses Core-level INSERT to preserve original IDs from SQLite.
Resets PostgreSQL sequences after migration.
"""
import asyncio
import os
import aiosqlite
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy import text
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

SQLITE_PATH = os.getenv("SQLITE_PATH", "server_data/data/bot.db")

# Agar default path da yo'q bo'lsa, boshqa joylarni tekshirish
if not os.path.exists(SQLITE_PATH):
    for alt_path in ["data/bot.db", "/app/data/bot.db", "bot.db"]:
        if os.path.exists(alt_path):
            SQLITE_PATH = alt_path
            break


def parse_datetime(value: str | None) -> datetime:
    """SQLite datetime stringini Python datetime ga o'girish."""
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return datetime.now()


async def reset_sequence(
    conn, table_name: str, column: str = "id"
) -> None:
    """PostgreSQL sequence ni max(id) + 1 ga qaytarish."""
    seq_name = f"{table_name}_{column}_seq"
    result = await conn.execute(
        text(f"SELECT MAX({column}) FROM {table_name}")
    )
    max_id = result.scalar()
    if max_id is not None:
        await conn.execute(
            text(
                f"SELECT setval('{seq_name}', :max_val, true)"
            ),
            {"max_val": max_id},
        )
        logger.info(
            f"   🔄 Sequence {seq_name} reset to {max_id}"
        )


async def migrate_data() -> None:
    """Main migration function."""
    logger.info("=" * 60)
    logger.info("🚀 Starting migration from SQLite to PostgreSQL")
    logger.info("=" * 60)

    if not os.path.exists(SQLITE_PATH):
        logger.error(
            f"❌ SQLite database not found: {SQLITE_PATH}"
        )
        return

    # Create PostgreSQL engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Drop and recreate all tables
    logger.info("📋 Creating PostgreSQL tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables created")

    # Connect to SQLite
    logger.info(f"📂 Opening SQLite database: {SQLITE_PATH}")
    async with aiosqlite.connect(SQLITE_PATH) as sqlite_db:
        sqlite_db.row_factory = aiosqlite.Row

        # Use a raw connection for Core-level inserts
        async with engine.begin() as conn:
            try:
                # ─── 1. Branches ───
                logger.info("\n1️⃣ Migrating branches...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM branches"
                )
                branches = await cursor.fetchall()
                if branches:
                    rows = [
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "address": row["address"],
                            "created_at": parse_datetime(
                                row["created_at"]
                            ),
                        }
                        for row in branches
                    ]
                    await conn.execute(
                        Branch.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(branches)} branches"
                )

                # ─── 2. Employees ───
                logger.info("\n2️⃣ Migrating employees...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM employees"
                )
                employees = await cursor.fetchall()
                if employees:
                    rows = [
                        {
                            "id": row["id"],
                            "telegram_id": row["telegram_id"],
                            "first_name": row["first_name"],
                            "last_name": row["last_name"],
                            "branch_id": row["branch_id"],
                            "shift": row["shift"],
                            "is_active": bool(row["is_active"]),
                            "created_at": parse_datetime(
                                row["created_at"]
                            ),
                        }
                        for row in employees
                    ]
                    await conn.execute(
                        Employee.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(employees)} employees"
                )

                # ─── 3. Tasks ───
                logger.info("\n3️⃣ Migrating tasks...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM tasks"
                )
                tasks = await cursor.fetchall()
                if tasks:
                    rows = []
                    for row in tasks:
                        rows.append(
                            {
                                "id": row["id"],
                                "title": row["title"],
                                "description": row["description"],
                                "task_type": row["task_type"],
                                "result_type": row["result_type"],
                                "shift": row["shift"],
                                "start_time": parse_datetime(
                                    row["start_time"]
                                ),
                                "deadline": parse_datetime(
                                    row["deadline"]
                                ),
                                "is_active": bool(
                                    row["is_active"]
                                ),
                                "created_at": parse_datetime(
                                    row["created_at"]
                                ),
                            }
                        )
                    await conn.execute(
                        Task.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(tasks)} tasks"
                )

                # ─── 4. Task-Branch relationships ───
                logger.info(
                    "\n4️⃣ Migrating task-branch relationships..."
                )
                cursor = await sqlite_db.execute(
                    "SELECT * FROM task_branches"
                )
                task_branches = await cursor.fetchall()
                if task_branches:
                    rows = [
                        {
                            "id": row["id"],
                            "task_id": row["task_id"],
                            "branch_id": row["branch_id"],
                        }
                        for row in task_branches
                    ]
                    await conn.execute(
                        TaskBranch.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(task_branches)} "
                    f"task-branch relationships"
                )

                # ─── 5. Task Results ───
                logger.info("\n5️⃣ Migrating task results...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM task_results"
                )
                task_results = await cursor.fetchall()
                if task_results:
                    rows = [
                        {
                            "id": row["id"],
                            "task_id": row["task_id"],
                            "employee_id": row["employee_id"],
                            "result_text": row["result_text"],
                            "result_photo_id": row[
                                "result_photo_id"
                            ],
                            "file_unique_id": row[
                                "file_unique_id"
                            ],
                            "is_late": bool(row["is_late"]),
                            "submitted_at": parse_datetime(
                                row["submitted_at"]
                            ),
                        }
                        for row in task_results
                    ]
                    await conn.execute(
                        TaskResult.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(task_results)} "
                    f"task results"
                )

                # ─── 6. Used Photos ───
                logger.info("\n6️⃣ Migrating used photos...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM used_photos"
                )
                used_photos = await cursor.fetchall()
                if used_photos:
                    rows = [
                        {
                            "id": row["id"],
                            "file_unique_id": row[
                                "file_unique_id"
                            ],
                            "task_id": row["task_id"],
                            "employee_id": row["employee_id"],
                            "used_at": parse_datetime(
                                row["used_at"]
                            ),
                        }
                        for row in used_photos
                    ]
                    await conn.execute(
                        UsedPhoto.__table__.insert(), rows
                    )
                logger.info(
                    f"   ✅ Migrated {len(used_photos)} "
                    f"used photos"
                )

                # ─── 7. Sent Notifications ───
                logger.info(
                    "\n7️⃣ Migrating sent notifications..."
                )
                try:
                    cursor = await sqlite_db.execute(
                        "SELECT * FROM sent_notifications"
                    )
                    notifications = await cursor.fetchall()
                    if notifications:
                        rows = [
                            {
                                "id": row["id"],
                                "task_id": row["task_id"],
                                "employee_id": row[
                                    "employee_id"
                                ],
                                "notification_type": row[
                                    "notification_type"
                                ],
                                "sent_at": parse_datetime(
                                    row["sent_at"]
                                ),
                            }
                            for row in notifications
                        ]
                        await conn.execute(
                            SentNotification.__table__.insert(),
                            rows,
                        )
                    logger.info(
                        f"   ✅ Migrated {len(notifications)} "
                        f"notifications"
                    )
                except Exception as e:
                    logger.warning(
                        f"   ⚠️ Notifications table: {e}"
                    )

                # ─── 8. Reset all sequences ───
                logger.info(
                    "\n8️⃣ Resetting PostgreSQL sequences..."
                )
                for table_name in [
                    "branches",
                    "employees",
                    "tasks",
                    "task_branches",
                    "task_results",
                    "used_photos",
                    "sent_notifications",
                ]:
                    try:
                        await reset_sequence(conn, table_name)
                    except Exception as e:
                        logger.warning(
                            f"   ⚠️ Sequence reset for "
                            f"{table_name}: {e}"
                        )

                logger.info("\n" + "=" * 60)
                logger.info("✅ Migration completed successfully!")
                logger.info("=" * 60)

            except Exception as e:
                logger.error(
                    f"\n❌ Migration failed: {e}", exc_info=True
                )
                raise

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_data())
        print(
            "\n🎉 All data successfully migrated to PostgreSQL!"
        )
        print(
            "You can now start the bot with: python3 main.py"
        )
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        exit(1)
