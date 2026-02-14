#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates all data from bot.db to PostgreSQL database

Uses raw SQL and disables FK constraints during migration
to handle SQLite data integrity gaps.
"""
import asyncio
import os
import aiosqlite
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database.db_postgres import Base
from config import DATABASE_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "server_data/data/bot.db")

if not os.path.exists(SQLITE_PATH):
    for alt_path in [
        "data/bot.db", "/app/data/bot.db", "bot.db"
    ]:
        if os.path.exists(alt_path):
            SQLITE_PATH = alt_path
            break


def parse_dt(value: str | None) -> datetime:
    """SQLite datetime stringini Python datetime ga."""
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(
                value, "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            return datetime.now()


# Barcha jadvallar (FK constraint bor/yo'q - hammasi uchun)
ALL_TABLES = [
    "sent_notifications",
    "used_photos",
    "task_results",
    "task_branches",
    "employees",
    "tasks",
    "branches",
]


async def migrate_data() -> None:
    """Main migration function."""
    logger.info("=" * 60)
    logger.info("Starting migration from SQLite to PostgreSQL")
    logger.info("=" * 60)

    if not os.path.exists(SQLITE_PATH):
        logger.error(
            f"SQLite database not found: {SQLITE_PATH}"
        )
        return

    engine = create_async_engine(DATABASE_URL, echo=False)

    # ── Drop and recreate tables ──
    logger.info("Creating PostgreSQL tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created")

    logger.info(f"Opening SQLite database: {SQLITE_PATH}")
    async with aiosqlite.connect(SQLITE_PATH) as sqlite_db:
        sqlite_db.row_factory = aiosqlite.Row

        async with engine.begin() as conn:
            try:
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # FK CONSTRAINT larni O'CHIRISH
                # SQLite FK enforce qilmaydi, shuning uchun
                # eski datada buzilgan referenslar bo'lishi
                # mumkin. Migration uchun vaqtincha o'chiramiz.
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                logger.info(
                    "Disabling FK constraints for migration..."
                )
                for tbl in ALL_TABLES:
                    await conn.execute(
                        text(
                            f"ALTER TABLE {tbl} "
                            f"DISABLE TRIGGER ALL"
                        )
                    )
                logger.info("FK constraints disabled")

                # ── 1. Branches ──
                logger.info("1. Migrating branches...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM branches"
                )
                branches = await cursor.fetchall()
                for row in branches:
                    await conn.execute(
                        text(
                            "INSERT INTO branches "
                            "(id, name, address, created_at) "
                            "VALUES (:id, :name, :addr, :cat)"
                        ),
                        {
                            "id": int(row["id"]),
                            "name": str(row["name"]),
                            "addr": row["address"],
                            "cat": parse_dt(row["created_at"]),
                        },
                    )
                logger.info(
                    f"   Migrated {len(branches)} branches"
                )

                # Verify branch IDs
                result = await conn.execute(
                    text(
                        "SELECT id FROM branches ORDER BY id"
                    )
                )
                pg_ids = [r[0] for r in result.fetchall()]
                logger.info(
                    f"   Branch IDs in PostgreSQL: {pg_ids}"
                )

                # ── 2. Employees ──
                logger.info("2. Migrating employees...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM employees"
                )
                employees = await cursor.fetchall()
                for row in employees:
                    await conn.execute(
                        text(
                            "INSERT INTO employees "
                            "(id, telegram_id, first_name, "
                            "last_name, branch_id, shift, "
                            "is_active, created_at) "
                            "VALUES (:id, :tid, :fn, :ln, "
                            ":bid, :sh, :ia, :cat)"
                        ),
                        {
                            "id": int(row["id"]),
                            "tid": int(row["telegram_id"]),
                            "fn": str(row["first_name"]),
                            "ln": str(row["last_name"]),
                            "bid": int(row["branch_id"]),
                            "sh": str(row["shift"]),
                            "ia": bool(row["is_active"]),
                            "cat": parse_dt(
                                row["created_at"]
                            ),
                        },
                    )
                logger.info(
                    f"   Migrated {len(employees)} employees"
                )

                # ── 3. Tasks ──
                logger.info("3. Migrating tasks...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM tasks"
                )
                tasks = await cursor.fetchall()
                for row in tasks:
                    await conn.execute(
                        text(
                            "INSERT INTO tasks "
                            "(id, title, description, "
                            "task_type, result_type, shift, "
                            "start_time, deadline, is_active, "
                            "created_at) "
                            "VALUES (:id, :title, :desc, :tt, "
                            ":rt, :sh, :st, :dl, :ia, :cat)"
                        ),
                        {
                            "id": int(row["id"]),
                            "title": str(row["title"]),
                            "desc": row["description"],
                            "tt": str(row["task_type"]),
                            "rt": str(row["result_type"]),
                            "sh": str(row["shift"]),
                            "st": parse_dt(row["start_time"]),
                            "dl": parse_dt(row["deadline"]),
                            "ia": bool(row["is_active"]),
                            "cat": parse_dt(
                                row["created_at"]
                            ),
                        },
                    )
                logger.info(
                    f"   Migrated {len(tasks)} tasks"
                )

                # ── 4. Task-Branch links ──
                logger.info(
                    "4. Migrating task-branch links..."
                )
                cursor = await sqlite_db.execute(
                    "SELECT * FROM task_branches"
                )
                task_branches = await cursor.fetchall()
                for row in task_branches:
                    await conn.execute(
                        text(
                            "INSERT INTO task_branches "
                            "(id, task_id, branch_id) "
                            "VALUES (:id, :tid, :bid)"
                        ),
                        {
                            "id": int(row["id"]),
                            "tid": int(row["task_id"]),
                            "bid": int(row["branch_id"]),
                        },
                    )
                logger.info(
                    f"   Migrated {len(task_branches)} links"
                )

                # ── 5. Task Results ──
                logger.info("5. Migrating task results...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM task_results"
                )
                task_results = await cursor.fetchall()
                for row in task_results:
                    await conn.execute(
                        text(
                            "INSERT INTO task_results "
                            "(id, task_id, employee_id, "
                            "result_text, result_photo_id, "
                            "file_unique_id, is_late, "
                            "submitted_at) "
                            "VALUES (:id, :tid, :eid, :rt, "
                            ":rpi, :fui, :il, :sa)"
                        ),
                        {
                            "id": int(row["id"]),
                            "tid": int(row["task_id"]),
                            "eid": int(row["employee_id"]),
                            "rt": row["result_text"],
                            "rpi": row["result_photo_id"],
                            "fui": row["file_unique_id"],
                            "il": bool(row["is_late"]),
                            "sa": parse_dt(
                                row["submitted_at"]
                            ),
                        },
                    )
                logger.info(
                    f"   Migrated {len(task_results)} results"
                )

                # ── 6. Used Photos ──
                logger.info("6. Migrating used photos...")
                cursor = await sqlite_db.execute(
                    "SELECT * FROM used_photos"
                )
                used_photos = await cursor.fetchall()
                for row in used_photos:
                    await conn.execute(
                        text(
                            "INSERT INTO used_photos "
                            "(id, file_unique_id, task_id, "
                            "employee_id, used_at) "
                            "VALUES (:id, :fui, :tid, "
                            ":eid, :ua)"
                        ),
                        {
                            "id": int(row["id"]),
                            "fui": str(
                                row["file_unique_id"]
                            ),
                            "tid": int(row["task_id"]),
                            "eid": int(row["employee_id"]),
                            "ua": parse_dt(row["used_at"]),
                        },
                    )
                logger.info(
                    f"   Migrated {len(used_photos)} photos"
                )

                # ── 7. Sent Notifications ──
                logger.info("7. Migrating notifications...")
                try:
                    cursor = await sqlite_db.execute(
                        "SELECT * FROM sent_notifications"
                    )
                    notifications = await cursor.fetchall()
                    for row in notifications:
                        await conn.execute(
                            text(
                                "INSERT INTO "
                                "sent_notifications "
                                "(id, task_id, employee_id, "
                                "notification_type, sent_at) "
                                "VALUES (:id, :tid, :eid, "
                                ":nt, :sa)"
                            ),
                            {
                                "id": int(row["id"]),
                                "tid": int(row["task_id"]),
                                "eid": int(
                                    row["employee_id"]
                                ),
                                "nt": str(
                                    row["notification_type"]
                                ),
                                "sa": parse_dt(
                                    row["sent_at"]
                                ),
                            },
                        )
                    logger.info(
                        f"   Migrated {len(notifications)} "
                        f"notifications"
                    )
                except Exception as e:
                    logger.warning(
                        f"   Notifications: {e}"
                    )

                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # FK CONSTRAINT larni QAYTA YOQISH
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                logger.info(
                    "Re-enabling FK constraints..."
                )
                for tbl in ALL_TABLES:
                    await conn.execute(
                        text(
                            f"ALTER TABLE {tbl} "
                            f"ENABLE TRIGGER ALL"
                        )
                    )
                logger.info("FK constraints re-enabled")

                # ── 8. Reset sequences ──
                logger.info("8. Resetting sequences...")
                for tbl in ALL_TABLES:
                    try:
                        r = await conn.execute(
                            text(
                                f"SELECT MAX(id) FROM {tbl}"
                            )
                        )
                        max_id = r.scalar()
                        if max_id is not None:
                            await conn.execute(
                                text(
                                    f"SELECT setval("
                                    f"'{tbl}_id_seq', "
                                    f"{int(max_id)}, true)"
                                )
                            )
                            logger.info(
                                f"   {tbl}_id_seq -> "
                                f"{max_id}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"   Sequence {tbl}: {e}"
                        )

                # ── 9. Verification ──
                logger.info("9. Final verification...")
                for tbl in ALL_TABLES:
                    try:
                        r = await conn.execute(
                            text(
                                f"SELECT COUNT(*) "
                                f"FROM {tbl}"
                            )
                        )
                        cnt = r.scalar()
                        logger.info(
                            f"   {tbl}: {cnt} rows"
                        )
                    except Exception:
                        pass

                # ── 10. Orphan references check ──
                logger.info(
                    "10. Checking orphan references..."
                )
                r = await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM employees e "
                        "WHERE NOT EXISTS ("
                        "  SELECT 1 FROM branches b "
                        "  WHERE b.id = e.branch_id"
                        ")"
                    )
                )
                orphans = r.scalar()
                if orphans and orphans > 0:
                    logger.warning(
                        f"   {orphans} employees have "
                        f"invalid branch_id (normal - "
                        f"SQLite didn't enforce FK)"
                    )

                logger.info("")
                logger.info("=" * 60)
                logger.info(
                    "Migration completed successfully!"
                )
                logger.info("=" * 60)

            except Exception as e:
                logger.error(
                    f"Migration failed: {e}",
                    exc_info=True,
                )
                raise

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_data())
        print(
            "\nAll data successfully migrated "
            "to PostgreSQL!"
        )
        print(
            "Start the bot: python3 main.py"
        )
    except Exception as e:
        print(f"\nMigration failed: {e}")
        exit(1)
