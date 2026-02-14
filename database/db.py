"""
Ma'lumotlar bazasi bilan ishlash uchun barcha funksiyalar
Connection pool va xatolarni tutish bilan
"""
import aiosqlite
from datetime import datetime
from typing import Optional, List, Tuple
import os
import logging
import asyncio
from contextlib import asynccontextmanager

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Connection pool
_db_pool: List[aiosqlite.Connection] = []
_pool_size = 5
_pool_lock = asyncio.Lock()


async def get_connection():
    """Database connection olish (pool'dan)"""
    async with _pool_lock:
        if _db_pool:
            conn = _db_pool.pop()
            try:
                # Connection hali ishlayotganini tekshirish
                await conn.execute("SELECT 1")
                return conn
            except Exception:
                pass

        # Yangi connection yaratish
        conn = await aiosqlite.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=30000")
        return conn


async def release_connection(conn):
    """Connection ni pool ga qaytarish"""
    async with _pool_lock:
        if len(_db_pool) < _pool_size:
            _db_pool.append(conn)
        else:
            await conn.close()


@asynccontextmanager
async def get_db():
    """Context manager for database connection"""
    conn = await get_connection()
    try:
        yield conn
    finally:
        await release_connection(conn)


async def close_db():
    """Barcha connectionlarni yopish"""
    async with _pool_lock:
        for conn in _db_pool:
            try:
                await conn.close()
            except Exception:
                pass
        _db_pool.clear()
    logger.info("Database connections closed")


async def init_db():
    """Ma'lumotlar bazasini yaratish"""
    os.makedirs(os.path.dirname(DATABASE_PATH) or "data", exist_ok=True)

    async with get_db() as db:
        # Filiallar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Xodimlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                branch_id INTEGER NOT NULL,
                shift TEXT NOT NULL CHECK(shift IN ('kunduzgi', 'kechki')),
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
            )
        """)

        # Vazifalar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                task_type TEXT NOT NULL CHECK(task_type IN ('bir_martalik', 'har_kunlik')),
                result_type TEXT NOT NULL CHECK(result_type IN ('matn', 'rasm')),
                shift TEXT NOT NULL CHECK(shift IN ('kunduzgi', 'kechki', 'hammasi')),
                start_time TIMESTAMP NOT NULL,
                deadline TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Vazifa-Filial bog'lanish jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
                UNIQUE(task_id, branch_id)
            )
        """)

        # Vazifa natijalari jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                result_text TEXT,
                result_photo_id TEXT,
                file_unique_id TEXT,
                is_late INTEGER DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                UNIQUE(task_id, employee_id)
            )
        """)

        # Foydalanilgan rasmlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS used_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_unique_id TEXT UNIQUE NOT NULL,
                task_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Yuborilgan bildirishnomalar jadvali (takrorlanishni oldini olish uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, employee_id, notification_type)
            )
        """)

        # Indekslar
        await db.execute("CREATE INDEX IF NOT EXISTS idx_employees_telegram_id ON employees(telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_employees_branch_id ON employees(branch_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_is_active ON tasks(is_active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_branches_task_id ON task_branches(task_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON task_results(task_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sent_notifications ON sent_notifications(task_id, employee_id, notification_type)")

        await db.commit()
        logger.info("✅ Database initialized successfully")


# ============== FILIALLAR ==============

async def create_branch(name: str, address: str = None) -> int:
    """Yangi filial yaratish"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO branches (name, address) VALUES (?, ?)",
            (name, address)
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_branches() -> List[dict]:
    """Barcha filiallarni olish (nomdagi raqam bo'yicha tartiblangan)"""
    import re

    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM branches")
        rows = await cursor.fetchall()
        branches = [dict(row) for row in rows]

    def extract_number(name: str) -> int:
        """Nomdan raqamni ajratib olish"""
        # Nomdagi barcha raqamlarni topish
        numbers = re.findall(r'\d+', name)
        if numbers:
            # Birinchi topilgan raqamni qaytarish
            return int(numbers[0])
        # Raqam yo'q bo'lsa, oxiriga qo'yish
        return 999999

    # Nomdagi raqam bo'yicha tartiblash
    branches.sort(key=lambda x: (extract_number(x['name']), x['name']))
    return branches


async def get_branch(branch_id: int) -> Optional[dict]:
    """Filial ma'lumotlarini olish"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM branches WHERE id = ?", (branch_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_branch(branch_id: int, name: str, address: str = None) -> bool:
    """Filialni yangilash"""
    async with get_db() as db:
        await db.execute(
            "UPDATE branches SET name = ?, address = ? WHERE id = ?",
            (name, address, branch_id)
        )
        await db.commit()
        return True


async def delete_branch(branch_id: int) -> bool:
    """Filialni o'chirish"""
    async with get_db() as db:
        await db.execute("DELETE FROM branches WHERE id = ?", (branch_id,))
        await db.commit()
        return True


async def get_branch_employees_count(branch_id: int) -> int:
    """Filialdagi xodimlar sonini olish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM employees WHERE branch_id = ? AND is_active = 1",
            (branch_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ============== XODIMLAR ==============

async def create_employee(telegram_id: int, first_name: str, last_name: str,
                          branch_id: int, shift: str) -> int:
    """Yangi xodim yaratish"""
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO employees (telegram_id, first_name, last_name, branch_id, shift)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, first_name, last_name, branch_id, shift)
        )
        await db.commit()
        return cursor.lastrowid


async def get_employee_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Telegram ID orqali xodimni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT e.*, b.name as branch_name 
               FROM employees e 
               JOIN branches b ON e.branch_id = b.id 
               WHERE e.telegram_id = ? AND e.is_active = 1""",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_employee(employee_id: int) -> Optional[dict]:
    """ID orqali xodimni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT e.*, b.name as branch_name 
               FROM employees e 
               JOIN branches b ON e.branch_id = b.id 
               WHERE e.id = ?""",
            (employee_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_employee(employee_id: int, first_name: str = None, last_name: str = None,
                          branch_id: int = None, shift: str = None) -> bool:
    """Xodim ma'lumotlarini yangilash"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
        emp = await cursor.fetchone()
        if not emp:
            return False

        new_first_name = first_name if first_name else emp['first_name']
        new_last_name = last_name if last_name else emp['last_name']
        new_branch_id = branch_id if branch_id else emp['branch_id']
        new_shift = shift if shift else emp['shift']

        await db.execute(
            """UPDATE employees 
               SET first_name = ?, last_name = ?, branch_id = ?, shift = ?
               WHERE id = ?""",
            (new_first_name, new_last_name, new_branch_id, new_shift, employee_id)
        )
        await db.commit()
        return True


async def update_employee_by_telegram_id(telegram_id: int, first_name: str = None,
                                          last_name: str = None, branch_id: int = None,
                                          shift: str = None) -> bool:
    """Telegram ID orqali xodim ma'lumotlarini yangilash"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM employees WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,)
        )
        emp = await cursor.fetchone()
        if not emp:
            return False

        new_first_name = first_name if first_name else emp['first_name']
        new_last_name = last_name if last_name else emp['last_name']
        new_branch_id = branch_id if branch_id else emp['branch_id']
        new_shift = shift if shift else emp['shift']

        await db.execute(
            """UPDATE employees 
               SET first_name = ?, last_name = ?, branch_id = ?, shift = ?
               WHERE telegram_id = ?""",
            (new_first_name, new_last_name, new_branch_id, new_shift, telegram_id)
        )
        await db.commit()
        return True


async def delete_employee(employee_id: int) -> bool:
    """Xodimni o'chirish (soft delete)"""
    async with get_db() as db:
        await db.execute(
            "UPDATE employees SET is_active = 0 WHERE id = ?",
            (employee_id,)
        )
        await db.commit()
        return True


async def delete_employee_by_telegram_id(telegram_id: int) -> bool:
    """Telegram ID orqali xodimni o'chirish"""
    async with get_db() as db:
        await db.execute(
            "UPDATE employees SET is_active = 0 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()
        return True


async def get_all_employees() -> List[dict]:
    """Barcha faol xodimlarni olish (filial raqami bo'yicha tartiblangan)"""
    import re

    async with get_db() as db:
        cursor = await db.execute(
            """SELECT e.*, b.name as branch_name 
               FROM employees e 
               JOIN branches b ON e.branch_id = b.id 
               WHERE e.is_active = 1"""
        )
        rows = await cursor.fetchall()
        employees = [dict(row) for row in rows]

    def extract_number(name: str) -> int:
        """Nomdan raqamni ajratib olish"""
        numbers = re.findall(r'\d+', name)
        if numbers:
            return int(numbers[0])
        return 999999

    # Filial raqami bo'yicha, keyin ism bo'yicha tartiblash
    employees.sort(key=lambda x: (extract_number(x['branch_name']), x['first_name']))
    return employees


async def get_employees_by_branch(branch_id: int) -> List[dict]:
    """Filial bo'yicha xodimlarni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT e.*, b.name as branch_name 
               FROM employees e 
               JOIN branches b ON e.branch_id = b.id 
               WHERE e.branch_id = ? AND e.is_active = 1
               ORDER BY e.first_name""",
            (branch_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_total_employees_count() -> int:
    """Jami xodimlar sonini olish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM employees WHERE is_active = 1"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ============== VAZIFALAR ==============

async def create_task(title: str, description: str, task_type: str, result_type: str,
                      shift: str, start_time: datetime, deadline: datetime,
                      branch_ids: List[int]) -> int:
    """Yangi vazifa yaratish"""
    async with get_db() as db:
        # start_time va deadline ni string formatga o'tkazish
        if isinstance(start_time, datetime):
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_time_str = start_time

        if isinstance(deadline, datetime):
            deadline_str = deadline.strftime("%Y-%m-%d %H:%M:%S")
        else:
            deadline_str = deadline

        cursor = await db.execute(
            """INSERT INTO tasks (title, description, task_type, result_type, shift, start_time, deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, description, task_type, result_type, shift, start_time_str, deadline_str)
        )
        task_id = cursor.lastrowid

        # Vazifa-filial bog'lanishlarini qo'shish
        for branch_id in branch_ids:
            await db.execute(
                "INSERT INTO task_branches (task_id, branch_id) VALUES (?, ?)",
                (task_id, branch_id)
            )

        await db.commit()
        return task_id


async def get_task(task_id: int) -> Optional[dict]:
    """Vazifa ma'lumotlarini olish"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_task(task_id: int, title: str = None, description: str = None,
                      task_type: str = None, result_type: str = None, shift: str = None,
                      start_time: datetime = None, deadline: datetime = None) -> bool:
    """Vazifani yangilash"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            return False

        new_title = title if title else task['title']
        new_description = description if description is not None else task['description']
        new_task_type = task_type if task_type else task['task_type']
        new_result_type = result_type if result_type else task['result_type']
        new_shift = shift if shift else task['shift']

        if start_time:
            new_start_time = start_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(start_time, datetime) else start_time
        else:
            new_start_time = task['start_time']

        if deadline:
            new_deadline = deadline.strftime("%Y-%m-%d %H:%M:%S") if isinstance(deadline, datetime) else deadline
        else:
            new_deadline = task['deadline']

        await db.execute(
            """UPDATE tasks 
               SET title = ?, description = ?, task_type = ?, result_type = ?, 
                   shift = ?, start_time = ?, deadline = ?
               WHERE id = ?""",
            (new_title, new_description, new_task_type, new_result_type,
             new_shift, new_start_time, new_deadline, task_id)
        )
        await db.commit()
        return True


async def delete_task(task_id: int) -> bool:
    """Vazifani o'chirish"""
    async with get_db() as db:
        await db.execute("DELETE FROM task_branches WHERE task_id = ?", (task_id,))
        await db.execute("DELETE FROM task_results WHERE task_id = ?", (task_id,))
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()
        return True


async def deactivate_task(task_id: int) -> bool:
    """Vazifani deaktivatsiya qilish"""
    async with get_db() as db:
        await db.execute(
            "UPDATE tasks SET is_active = 0 WHERE id = ?",
            (task_id,)
        )
        await db.commit()
        return True


async def get_task_branches(task_id: int) -> List[dict]:
    """Vazifaga tegishli filiallarni olish (nomdagi raqam bo'yicha tartiblangan)"""
    import re

    async with get_db() as db:
        cursor = await db.execute(
            """SELECT b.* FROM branches b
               JOIN task_branches tb ON b.id = tb.branch_id
               WHERE tb.task_id = ?""",
            (task_id,)
        )
        rows = await cursor.fetchall()
        branches = [dict(row) for row in rows]

    def extract_number(name: str) -> int:
        numbers = re.findall(r'\d+', name)
        return int(numbers[0]) if numbers else 999999

    branches.sort(key=lambda x: (extract_number(x['name']), x['name']))
    return branches


async def get_active_tasks() -> List[dict]:
    """Faol vazifalarni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM tasks 
               WHERE is_active = 1 
               ORDER BY created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_employee_tasks(employee_id: int) -> List[dict]:
    """Xodimga tegishli vazifalarni olish (employee_id orqali)"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT branch_id, shift FROM employees WHERE id = ?",
            (employee_id,)
        )
        emp = await cursor.fetchone()
        if not emp:
            return []

        branch_id, emp_shift = emp['branch_id'], emp['shift']

        cursor = await db.execute(
            """SELECT DISTINCT t.*, 
                      CASE WHEN tr.id IS NOT NULL THEN 1 ELSE 0 END as is_completed,
                      tr.is_late
               FROM tasks t
               JOIN task_branches tb ON t.id = tb.task_id
               LEFT JOIN task_results tr ON t.id = tr.task_id AND tr.employee_id = ?
               WHERE tb.branch_id = ?
                 AND t.is_active = 1
                 AND (t.shift = 'hammasi' OR t.shift = ?)
               ORDER BY t.deadline ASC""",
            (employee_id, branch_id, emp_shift)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_employee_tasks_by_telegram_id(telegram_id: int) -> List[dict]:
    """Telegram ID orqali xodimga tegishli vazifalarni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, branch_id, shift FROM employees WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,)
        )
        emp = await cursor.fetchone()
        if not emp:
            return []

        employee_id = emp['id']
        branch_id = emp['branch_id']
        emp_shift = emp['shift']

        cursor = await db.execute(
            """SELECT DISTINCT t.*, 
                      CASE WHEN tr.id IS NOT NULL THEN 1 ELSE 0 END as is_completed,
                      COALESCE(tr.is_late, 0) as is_late
               FROM tasks t
               JOIN task_branches tb ON t.id = tb.task_id
               LEFT JOIN task_results tr ON t.id = tr.task_id AND tr.employee_id = ?
               WHERE tb.branch_id = ?
                 AND t.is_active = 1
                 AND (t.shift = 'hammasi' OR t.shift = ?)
               ORDER BY t.deadline ASC""",
            (employee_id, branch_id, emp_shift)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_employees_for_task(task_id: int) -> List[dict]:
    """Vazifaga tegishli barcha xodimlarni olish"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            return []

        shift = task['shift']

        cursor = await db.execute(
            "SELECT branch_id FROM task_branches WHERE task_id = ?",
            (task_id,)
        )
        branch_rows = await cursor.fetchall()
        branch_ids = [row['branch_id'] for row in branch_rows]

        if not branch_ids:
            return []

        placeholders = ','.join('?' * len(branch_ids))

        if shift == 'hammasi':
            query = f"""
                SELECT e.*, b.name as branch_name 
                FROM employees e
                JOIN branches b ON e.branch_id = b.id
                WHERE e.branch_id IN ({placeholders}) AND e.is_active = 1
            """
            params = branch_ids
        else:
            query = f"""
                SELECT e.*, b.name as branch_name 
                FROM employees e
                JOIN branches b ON e.branch_id = b.id
                WHERE e.branch_id IN ({placeholders}) AND e.is_active = 1 AND e.shift = ?
            """
            params = branch_ids + [shift]

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_daily_tasks() -> List[dict]:
    """Har kunlik vazifalarni olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM tasks 
               WHERE task_type = 'har_kunlik' AND is_active = 1"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============== NATIJALAR ==============

async def submit_task_result(task_id: int, employee_id: int, result_text: str = None,
                             result_photo_id: str = None, file_unique_id: str = None) -> Tuple[int, int]:
    """Vazifa natijasini yuborish"""
    async with get_db() as db:
        # Deadline o'tganligini tekshirish
        cursor = await db.execute(
            "SELECT deadline FROM tasks WHERE id = ?",
            (task_id,)
        )
        task = await cursor.fetchone()

        is_late = 0
        if task:
            try:
                deadline_str = task[0]
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
                    try:
                        deadline_dt = datetime.strptime(deadline_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    deadline_dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))

                if datetime.now() > deadline_dt:
                    is_late = 1
            except Exception:
                is_late = 0

        # Natijani saqlash
        cursor = await db.execute(
            """INSERT INTO task_results (task_id, employee_id, result_text, result_photo_id, file_unique_id, is_late)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, employee_id, result_text, result_photo_id, file_unique_id, is_late)
        )
        result_id = cursor.lastrowid

        # Agar rasm bo'lsa, used_photos ga qo'shish
        if file_unique_id:
            await db.execute(
                "INSERT OR IGNORE INTO used_photos (file_unique_id, task_id, employee_id) VALUES (?, ?, ?)",
                (file_unique_id, task_id, employee_id)
            )

        # Nechanchi bo'lib bajarganini hisoblash
        cursor = await db.execute(
            "SELECT COUNT(*) FROM task_results WHERE task_id = ?",
            (task_id,)
        )
        count = await cursor.fetchone()
        position = count[0] if count else 1

        await db.commit()
        return result_id, position


async def submit_task_result_by_telegram_id(task_id: int, telegram_id: int, result_text: str = None,
                                             result_photo_id: str = None, file_unique_id: str = None) -> Tuple[int, int]:
    """Telegram ID orqali vazifa natijasini yuborish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM employees WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,)
        )
        emp = await cursor.fetchone()
        if not emp:
            return 0, 0

        employee_id = emp['id']

    return await submit_task_result(task_id, employee_id, result_text, result_photo_id, file_unique_id)


async def check_photo_used(file_unique_id: str) -> bool:
    """Rasm avval ishlatilganligini tekshirish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM used_photos WHERE file_unique_id = ?",
            (file_unique_id,)
        )
        row = await cursor.fetchone()
        return row is not None


async def get_task_result(task_id: int, employee_id: int) -> Optional[dict]:
    """Xodimning vazifa natijasini olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT * FROM task_results 
               WHERE task_id = ? AND employee_id = ?""",
            (task_id, employee_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_task_result_by_telegram_id(task_id: int, telegram_id: int) -> Optional[dict]:
    """Telegram ID orqali natijani olish"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM employees WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,)
        )
        emp = await cursor.fetchone()
        if not emp:
            return None

        cursor = await db.execute(
            """SELECT * FROM task_results 
               WHERE task_id = ? AND employee_id = ?""",
            (task_id, emp['id'])
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def has_submitted_result(task_id: int, telegram_id: int) -> bool:
    """Natija yuborilganligini tekshirish"""
    result = await get_task_result_by_telegram_id(task_id, telegram_id)
    return result is not None


async def get_task_statistics(task_id: int) -> dict:
    """Vazifa statistikasini olish"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            return {}

        cursor = await db.execute(
            """SELECT DISTINCT b.id, b.name 
               FROM branches b
               JOIN task_branches tb ON b.id = tb.branch_id
               WHERE tb.task_id = ?""",
            (task_id,)
        )
        branches = await cursor.fetchall()

        result = {"branches": [], "task": dict(task)}

        for branch in branches:
            branch_id = branch['id']
            branch_name = branch['name']

            shift = task['shift']
            if shift == 'hammasi':
                shift_condition = "1=1"
            else:
                shift_condition = f"e.shift = '{shift}'"

            cursor = await db.execute(
                f"""SELECT e.id, e.first_name, e.last_name, e.telegram_id
                   FROM employees e
                   WHERE e.branch_id = ? AND e.is_active = 1 AND {shift_condition}""",
                (branch_id,)
            )
            employees = await cursor.fetchall()

            completed = []
            not_completed = []
            late = []

            for emp in employees:
                emp_id = emp['id']
                first_name = emp['first_name']
                last_name = emp['last_name']
                telegram_id = emp['telegram_id']

                cursor = await db.execute(
                    """SELECT tr.*, tr.result_text, tr.result_photo_id 
                       FROM task_results tr
                       WHERE tr.task_id = ? AND tr.employee_id = ?""",
                    (task_id, emp_id)
                )
                task_result = await cursor.fetchone()

                emp_info = {
                    "id": emp_id,
                    "name": f"{first_name} {last_name}",
                    "telegram_id": telegram_id,
                    "result": dict(task_result) if task_result else None
                }

                if task_result:
                    if task_result['is_late']:
                        late.append(emp_info)
                    else:
                        completed.append(emp_info)
                else:
                    not_completed.append(emp_info)

            result["branches"].append({
                "id": branch_id,
                "name": branch_name,
                "completed": completed,
                "not_completed": not_completed,
                "late": late
            })

        # Filiallarni nomdagi raqam bo'yicha tartiblash
        import re
        def extract_number(name: str) -> int:
            numbers = re.findall(r'\d+', name)
            return int(numbers[0]) if numbers else 999999

        result["branches"].sort(key=lambda x: (extract_number(x['name']), x['name']))

        return result


async def get_all_task_results(task_id: int) -> List[dict]:
    """Vazifaning barcha natijalarini olish"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT tr.*, e.first_name, e.last_name, e.telegram_id, b.name as branch_name
               FROM task_results tr
               JOIN employees e ON tr.employee_id = e.id
               JOIN branches b ON e.branch_id = b.id
               WHERE tr.task_id = ?
               ORDER BY tr.submitted_at ASC""",
            (task_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_task_result_by_id(result_id: int) -> Optional[dict]:
    """Natija ID orqali natijani olish (barcha ma'lumotlar bilan)"""
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT tr.*, e.first_name, e.last_name, b.name as branch_name,
                      t.title, t.id as task_id
               FROM task_results tr
               JOIN employees e ON tr.employee_id = e.id
               JOIN branches b ON e.branch_id = b.id
               JOIN tasks t ON tr.task_id = t.id
               WHERE tr.id = ?""", (result_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ============== BILDIRISHNOMALAR ==============

async def _ensure_notifications_table():
    """sent_notifications jadvali mavjudligini tekshirish va yaratish"""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, employee_id, notification_type)
            )
        """)
        await db.commit()


async def check_notification_sent(task_id: int, employee_id: int, notification_type: str) -> bool:
    """Bildirishnoma yuborilganligini tekshirish"""
    try:
        await _ensure_notifications_table()
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT id FROM sent_notifications 
                   WHERE task_id = ? AND employee_id = ? AND notification_type = ?""",
                (task_id, employee_id, notification_type)
            )
            row = await cursor.fetchone()
            return row is not None
    except Exception as e:
        logger.error(f"check_notification_sent error: {e}")
        return False


async def mark_notification_sent(task_id: int, employee_id: int, notification_type: str) -> bool:
    """Bildirishnoma yuborilganligini belgilash"""
    try:
        await _ensure_notifications_table()
        async with get_db() as db:
            await db.execute(
                """INSERT OR IGNORE INTO sent_notifications (task_id, employee_id, notification_type)
                   VALUES (?, ?, ?)""",
                (task_id, employee_id, notification_type)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"mark_notification_sent error: {e}")
        return False


async def clear_task_notifications(task_id: int) -> bool:
    """Vazifa bildirishnomalarini tozalash (kunlik vazifalar uchun)"""
    try:
        await _ensure_notifications_table()
        async with get_db() as db:
            await db.execute(
                "DELETE FROM sent_notifications WHERE task_id = ?",
                (task_id,)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"clear_task_notifications error: {e}")
        return False