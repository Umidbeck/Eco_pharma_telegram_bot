"""
PostgreSQL Database with SQLAlchemy ORM
Async support with asyncpg

MUHIM: Barcha vaqtlar NAIVE datetime sifatida saqlanadi.
Barcha vaqtlar Tashkent mahalliy vaqtini ifodalaydi.
"""
import re
import logging
import pytz
from datetime import datetime
from typing import Optional, List, Tuple
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime,
    Boolean, ForeignKey, UniqueConstraint,
    select, delete, update, func
)

from config import DATABASE_URL, TIMEZONE

logger = logging.getLogger(__name__)


def _tashkent_now():
    """Hozirgi Tashkent vaqtini NAIVE datetime sifatida qaytarish.
    DB default uchun ishlatiladi.
    """
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)

# SQLAlchemy Base
Base = declarative_base()

# Engine and Session
engine = None
async_session_maker = None


# ============== MODELS ==============

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_tashkent_now)

    employees = relationship(
        "Employee", back_populates="branch",
        cascade="all, delete-orphan"
    )
    task_branches = relationship(
        "TaskBranch", back_populates="branch",
        cascade="all, delete-orphan"
    )


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # BigInteger - Telegram ID 6+ mlrd bo'lishi mumkin
    telegram_id = Column(
        BigInteger, unique=True, nullable=False, index=True
    )
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    shift = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_tashkent_now)

    branch = relationship("Branch", back_populates="employees")
    task_results = relationship(
        "TaskResult", back_populates="employee",
        cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)
    result_type = Column(String(50), nullable=False)
    shift = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_tashkent_now)
    is_active = Column(Boolean, default=True, index=True)

    task_branches = relationship(
        "TaskBranch", back_populates="task",
        cascade="all, delete-orphan"
    )
    task_results = relationship(
        "TaskResult", back_populates="task",
        cascade="all, delete-orphan"
    )


class TaskBranch(Base):
    __tablename__ = "task_branches"
    __table_args__ = (
        UniqueConstraint('task_id', 'branch_id', name='uq_task_branch'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False
    )

    task = relationship("Task", back_populates="task_branches")
    branch = relationship("Branch", back_populates="task_branches")


class TaskResult(Base):
    __tablename__ = "task_results"
    __table_args__ = (
        UniqueConstraint(
            'task_id', 'employee_id', name='uq_task_employee'
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    result_text = Column(Text, nullable=True)
    result_photo_id = Column(String(500), nullable=True)
    file_unique_id = Column(String(500), nullable=True)
    is_late = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=_tashkent_now)

    task = relationship("Task", back_populates="task_results")
    employee = relationship("Employee", back_populates="task_results")


class UsedPhoto(Base):
    __tablename__ = "used_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_unique_id = Column(String(500), unique=True, nullable=False)
    task_id = Column(Integer, nullable=False)
    employee_id = Column(Integer, nullable=False)
    used_at = Column(DateTime, default=_tashkent_now)


class SentNotification(Base):
    """Yuborilgan bildirishnomalar jadvali.
    employee_id=0 admin uchun ishlatiladi, shuning uchun ForeignKey yo'q.
    """
    __tablename__ = "sent_notifications"
    __table_args__ = (
        UniqueConstraint(
            'task_id', 'employee_id', 'notification_type',
            name='uq_notification'
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    # ForeignKey yo'q - employee_id=0 admin uchun ishlatiladi
    employee_id = Column(Integer, nullable=False)
    notification_type = Column(String(100), nullable=False)
    sent_at = Column(DateTime, default=_tashkent_now)


# ============== ENGINE SETUP ==============

async def init_db():
    """Database initialization"""
    global engine, async_session_maker

    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ PostgreSQL database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise


async def close_db():
    """Close database connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("✅ Database connections closed")


@asynccontextmanager
async def get_session():
    """Get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            await session.close()


# ============== HELPER FUNCTIONS ==============

def _extract_number(name: str) -> int:
    """Nomdan raqamni ajratib olish (tartiblash uchun)"""
    numbers = re.findall(r'\d+', name)
    return int(numbers[0]) if numbers else 999999


def dict_from_row(row) -> Optional[dict]:
    """Convert SQLAlchemy row to dict.
    start_time va deadline ni string formatga o'tkazadi
    (eski kod bilan moslik uchun).
    """
    if row is None:
        return None
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        # datetime -> string (eski kod mosligini ta'minlash)
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        # Boolean -> int (eski kod mosligini ta'minlash)
        elif isinstance(value, bool):
            value = int(value)
        result[column.name] = value
    return result


# ============== BRANCHES ==============

async def create_branch(name: str, address: str = None) -> int:
    """Yangi filial yaratish"""
    async with get_session() as session:
        branch = Branch(name=name, address=address)
        session.add(branch)
        await session.commit()
        await session.refresh(branch)
        return branch.id


async def get_all_branches() -> List[dict]:
    """Barcha filiallarni olish (nomdagi raqam bo'yicha tartiblangan)"""
    async with get_session() as session:
        result = await session.execute(select(Branch))
        branches = result.scalars().all()
        branches_list = [dict_from_row(b) for b in branches]

    branches_list.sort(
        key=lambda x: (_extract_number(x['name']), x['name'])
    )
    return branches_list


async def get_branch(branch_id: int) -> Optional[dict]:
    """Filial ma'lumotlarini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        branch = result.scalar_one_or_none()
        return dict_from_row(branch) if branch else None


async def update_branch(
    branch_id: int, name: str, address: str = None
) -> bool:
    """Filialni yangilash"""
    async with get_session() as session:
        await session.execute(
            update(Branch)
            .where(Branch.id == branch_id)
            .values(name=name, address=address)
        )
        await session.commit()
        return True


async def delete_branch(branch_id: int) -> bool:
    """Filialni o'chirish"""
    async with get_session() as session:
        await session.execute(
            delete(Branch).where(Branch.id == branch_id)
        )
        await session.commit()
        return True


async def get_branch_employees_count(branch_id: int) -> int:
    """Filialdagi xodimlar sonini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(func.count(Employee.id))
            .where(
                Employee.branch_id == branch_id,
                Employee.is_active == True  # noqa: E712
            )
        )
        return result.scalar() or 0


# ============== EMPLOYEES ==============

async def create_employee(
    telegram_id: int, first_name: str, last_name: str,
    branch_id: int, shift: str
) -> int:
    """Yangi xodim yaratish"""
    async with get_session() as session:
        employee = Employee(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            branch_id=branch_id,
            shift=shift
        )
        session.add(employee)
        await session.commit()
        await session.refresh(employee)
        return employee.id


async def get_employee_by_telegram_id(
    telegram_id: int,
) -> Optional[dict]:
    """Telegram ID orqali xodimni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(
                Employee,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(
                Employee.telegram_id == telegram_id,
                Employee.is_active == True,  # noqa: E712
            )
        )
        row = result.first()
        if row:
            emp = dict_from_row(row[0])
            emp["branch_name"] = row[1] or "Noma'lum"
            return emp
        return None


async def get_employee(employee_id: int) -> Optional[dict]:
    """ID orqali xodimni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(
                Employee,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(Employee.id == employee_id)
        )
        row = result.first()
        if row:
            emp = dict_from_row(row[0])
            emp["branch_name"] = row[1] or "Noma'lum"
            return emp
        return None


async def update_employee(
    employee_id: int, first_name: str = None,
    last_name: str = None, branch_id: int = None,
    shift: str = None
) -> bool:
    """Xodim ma'lumotlarini yangilash"""
    async with get_session() as session:
        result = await session.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return False

        if first_name:
            emp.first_name = first_name
        if last_name:
            emp.last_name = last_name
        if branch_id:
            emp.branch_id = branch_id
        if shift:
            emp.shift = shift

        await session.commit()
        return True


async def update_employee_by_telegram_id(
    telegram_id: int, first_name: str = None,
    last_name: str = None, branch_id: int = None,
    shift: str = None
) -> bool:
    """Telegram ID orqali xodim ma'lumotlarini yangilash"""
    async with get_session() as session:
        result = await session.execute(
            select(Employee).where(
                Employee.telegram_id == telegram_id,
                Employee.is_active == True  # noqa: E712
            )
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return False

        if first_name:
            emp.first_name = first_name
        if last_name:
            emp.last_name = last_name
        if branch_id:
            emp.branch_id = branch_id
        if shift:
            emp.shift = shift

        await session.commit()
        return True


async def delete_employee(employee_id: int) -> bool:
    """Xodimni o'chirish (soft delete)"""
    async with get_session() as session:
        await session.execute(
            update(Employee)
            .where(Employee.id == employee_id)
            .values(is_active=False)
        )
        await session.commit()
        return True


async def delete_employee_by_telegram_id(telegram_id: int) -> bool:
    """Telegram ID orqali xodimni o'chirish"""
    async with get_session() as session:
        await session.execute(
            update(Employee)
            .where(Employee.telegram_id == telegram_id)
            .values(is_active=False)
        )
        await session.commit()
        return True


async def get_all_employees() -> List[dict]:
    """Barcha faol xodimlarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(
                Employee,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(Employee.is_active == True)  # noqa: E712
        )
        rows = result.all()
        employees = []
        for row in rows:
            emp = dict_from_row(row[0])
            emp["branch_name"] = row[1] or "Noma'lum"
            employees.append(emp)

    employees.sort(
        key=lambda x: (
            _extract_number(x['branch_name']),
            x['first_name']
        )
    )
    return employees


async def get_employees_by_branch(
    branch_id: int,
) -> List[dict]:
    """Filial bo'yicha xodimlarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(
                Employee,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(
                Employee.branch_id == branch_id,
                Employee.is_active == True,  # noqa: E712
            )
            .order_by(Employee.first_name)
        )
        rows = result.all()
        employees = []
        for row in rows:
            emp = dict_from_row(row[0])
            emp["branch_name"] = row[1] or "Noma'lum"
            employees.append(emp)
        return employees


async def get_total_employees_count() -> int:
    """Jami xodimlar sonini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(func.count(Employee.id))
            .where(Employee.is_active == True)  # noqa: E712
        )
        return result.scalar() or 0


# ============== TASKS ==============

async def create_task(
    title: str, description: str, task_type: str,
    result_type: str, shift: str, start_time: datetime,
    deadline: datetime, branch_ids: List[int]
) -> int:
    """Yangi vazifa yaratish.
    start_time va deadline NAIVE datetime bo'lishi kerak (Tashkent vaqti).
    """
    # Agar string bo'lsa, datetime ga o'tkazish
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline)

    # TZ-aware bo'lsa, Tashkent vaqtiga o'girib, naive qilish
    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
        tz = pytz.timezone(TIMEZONE)
        start_time = start_time.astimezone(tz).replace(tzinfo=None)
    if hasattr(deadline, 'tzinfo') and deadline.tzinfo is not None:
        tz = pytz.timezone(TIMEZONE)
        deadline = deadline.astimezone(tz).replace(tzinfo=None)

    async with get_session() as session:
        task = Task(
            title=title,
            description=description,
            task_type=task_type,
            result_type=result_type,
            shift=shift,
            start_time=start_time,
            deadline=deadline
        )
        session.add(task)
        await session.flush()

        for branch_id in branch_ids:
            task_branch = TaskBranch(
                task_id=task.id, branch_id=branch_id
            )
            session.add(task_branch)

        await session.commit()
        return task.id


async def get_task(task_id: int) -> Optional[dict]:
    """Vazifa ma'lumotlarini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        return dict_from_row(task) if task else None


async def update_task(
    task_id: int, title: str = None, description: str = None,
    task_type: str = None, result_type: str = None,
    shift: str = None, start_time: datetime = None,
    deadline: datetime = None
) -> bool:
    """Vazifani yangilash"""
    async with get_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return False

        if title:
            task.title = title
        if description is not None:
            task.description = description
        if task_type:
            task.task_type = task_type
        if result_type:
            task.result_type = result_type
        if shift:
            task.shift = shift
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            # TZ-aware bo'lsa, Tashkent vaqtiga o'girib, naive qilish
            if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
                tz = pytz.timezone(TIMEZONE)
                start_time = start_time.astimezone(tz).replace(tzinfo=None)
            task.start_time = start_time
        if deadline:
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline)
            # TZ-aware bo'lsa, Tashkent vaqtiga o'girib, naive qilish
            if hasattr(deadline, 'tzinfo') and deadline.tzinfo is not None:
                tz = pytz.timezone(TIMEZONE)
                deadline = deadline.astimezone(tz).replace(tzinfo=None)
            task.deadline = deadline

        await session.commit()
        return True


async def delete_task(task_id: int) -> bool:
    """Vazifani o'chirish"""
    async with get_session() as session:
        await session.execute(
            delete(Task).where(Task.id == task_id)
        )
        await session.commit()
        return True


async def deactivate_task(task_id: int) -> bool:
    """Vazifani deaktivatsiya qilish"""
    async with get_session() as session:
        await session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(is_active=False)
        )
        await session.commit()
        return True


async def get_task_branches(task_id: int) -> List[dict]:
    """Vazifaga tegishli filiallarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Branch)
            .join(TaskBranch, Branch.id == TaskBranch.branch_id)
            .where(TaskBranch.task_id == task_id)
        )
        branches = result.scalars().all()
        branches_list = [dict_from_row(b) for b in branches]

    branches_list.sort(
        key=lambda x: (_extract_number(x['name']), x['name'])
    )
    return branches_list


async def get_active_tasks() -> List[dict]:
    """Faol vazifalarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Task)
            .where(Task.is_active == True)  # noqa: E712
            .order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        return [dict_from_row(t) for t in tasks]


async def get_employee_tasks(employee_id: int) -> List[dict]:
    """Xodimga tegishli vazifalarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return []

        result = await session.execute(
            select(Task, TaskResult)
            .join(TaskBranch, Task.id == TaskBranch.task_id)
            .outerjoin(
                TaskResult,
                (Task.id == TaskResult.task_id)
                & (TaskResult.employee_id == employee_id),
            )
            .where(
                TaskBranch.branch_id == emp.branch_id,
                Task.is_active == True,  # noqa: E712
                (Task.shift == "hammasi")
                | (Task.shift == emp.shift),
            )
            .order_by(Task.deadline.asc())
        )

        rows = result.all()
        seen_ids = set()
        tasks = []
        for task, task_result in rows:
            if task.id in seen_ids:
                continue
            seen_ids.add(task.id)
            task_dict = dict_from_row(task)
            task_dict['is_completed'] = 1 if task_result else 0
            task_dict['is_late'] = (
                int(task_result.is_late) if task_result else 0
            )
            tasks.append(task_dict)

        return tasks


async def get_employee_tasks_by_telegram_id(
    telegram_id: int
) -> List[dict]:
    """Telegram ID orqali xodimga tegishli vazifalarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Employee).where(
                Employee.telegram_id == telegram_id,
                Employee.is_active == True  # noqa: E712
            )
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return []

    return await get_employee_tasks(emp.id)


async def get_employees_for_task(task_id: int) -> List[dict]:
    """Vazifaga tegishli barcha xodimlarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return []

        result = await session.execute(
            select(TaskBranch.branch_id)
            .where(TaskBranch.task_id == task_id)
        )
        branch_ids = [row[0] for row in result.all()]

        if not branch_ids:
            return []

        query = (
            select(
                Employee,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(
                Employee.branch_id.in_(branch_ids),
                Employee.is_active == True,  # noqa: E712
            )
        )

        if task.shift != 'hammasi':
            query = query.where(Employee.shift == task.shift)

        result = await session.execute(query)
        rows = result.all()

        employees = []
        for emp, branch_name in rows:
            emp_dict = dict_from_row(emp)
            emp_dict["branch_name"] = (
                branch_name or "Noma'lum"
            )
            employees.append(emp_dict)

        return employees


async def get_daily_tasks() -> List[dict]:
    """Har kunlik vazifalarni olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Task).where(
                Task.task_type == 'har_kunlik',
                Task.is_active == True  # noqa: E712
            )
        )
        tasks = result.scalars().all()
        return [dict_from_row(t) for t in tasks]


# ============== TASK RESULTS ==============

async def submit_task_result(
    task_id: int, employee_id: int,
    result_text: str = None,
    file_unique_id: str = None
) -> Tuple[int, int, bool]:
    """Vazifa natijasini yuborish"""
    async with get_session() as session:
        # Deadline o'tganligini tekshirish
        result = await session.execute(
            select(Task.deadline).where(Task.id == task_id)
        )
        deadline = result.scalar_one_or_none()

        is_late = False
        if deadline:
            # deadline datetime yoki string bo'lishi mumkin
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline)
                except Exception:
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"
                    ]:
                        try:
                            deadline = datetime.strptime(deadline, fmt)
                            break
                        except ValueError:
                            continue
            if isinstance(deadline, datetime):
                if _tashkent_now() > deadline:
                    is_late = True

        # Natijani saqlash
        task_result = TaskResult(
            task_id=task_id,
            employee_id=employee_id,
            result_text=result_text,
            file_unique_id=file_unique_id,
            is_late=is_late
        )
        session.add(task_result)

        # Agar rasm bo'lsa, used_photos ga qo'shish
        if file_unique_id:
            used_photo = UsedPhoto(
                file_unique_id=file_unique_id,
                task_id=task_id,
                employee_id=employee_id
            )
            session.add(used_photo)

        await session.flush()
        result_id = task_result.id

        # Nechanchi bo'lib bajarganini hisoblash
        result = await session.execute(
            select(func.count(TaskResult.id))
            .where(TaskResult.task_id == task_id)
        )
        position = result.scalar() or 1

        await session.commit()
        return result_id, position, is_late


async def submit_task_result_by_telegram_id(
    task_id: int, telegram_id: int,
    result_text: str = None,
    file_unique_id: str = None
) -> Tuple[int, int, bool]:
    """Telegram ID orqali vazifa natijasini yuborish"""
    async with get_session() as session:
        result = await session.execute(
            select(Employee.id).where(
                Employee.telegram_id == telegram_id,
                Employee.is_active == True  # noqa: E712
            )
        )
        emp_id = result.scalar_one_or_none()
        if not emp_id:
            return 0, 0, False

    return await submit_task_result(
        task_id, emp_id, result_text, file_unique_id
    )


async def check_photo_used(file_unique_id: str) -> bool:
    """Rasm avval ishlatilganligini tekshirish"""
    async with get_session() as session:
        result = await session.execute(
            select(UsedPhoto.id)
            .where(UsedPhoto.file_unique_id == file_unique_id)
        )
        return result.scalar_one_or_none() is not None


async def get_task_result(
    task_id: int, employee_id: int
) -> Optional[dict]:
    """Xodimning vazifa natijasini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(TaskResult).where(
                TaskResult.task_id == task_id,
                TaskResult.employee_id == employee_id
            )
        )
        task_result = result.scalar_one_or_none()
        return dict_from_row(task_result) if task_result else None


async def get_task_result_by_telegram_id(
    task_id: int, telegram_id: int,
) -> Optional[dict]:
    """Telegram ID orqali natijani olish"""
    async with get_session() as session:
        result = await session.execute(
            select(TaskResult)
            .outerjoin(
                Employee,
                TaskResult.employee_id == Employee.id,
            )
            .where(
                TaskResult.task_id == task_id,
                Employee.telegram_id == telegram_id,
                Employee.is_active == True,  # noqa: E712
            )
        )
        task_result = result.scalar_one_or_none()
        return (
            dict_from_row(task_result)
            if task_result
            else None
        )


async def has_submitted_result(
    task_id: int, telegram_id: int
) -> bool:
    """Natija yuborilganligini tekshirish"""
    result = await get_task_result_by_telegram_id(
        task_id, telegram_id
    )
    return result is not None


async def get_task_statistics(task_id: int) -> dict:
    """Vazifa statistikasini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return {}

        result = await session.execute(
            select(Branch)
            .join(TaskBranch, Branch.id == TaskBranch.branch_id)
            .where(TaskBranch.task_id == task_id)
        )
        branches = result.scalars().all()

        stats = {"branches": [], "task": dict_from_row(task)}

        for branch in branches:
            query = select(Employee).where(
                Employee.branch_id == branch.id,
                Employee.is_active == True  # noqa: E712
            )

            if task.shift != 'hammasi':
                query = query.where(Employee.shift == task.shift)

            result = await session.execute(query)
            employees = result.scalars().all()

            completed = []
            not_completed = []
            late = []

            for emp in employees:
                result = await session.execute(
                    select(TaskResult).where(
                        TaskResult.task_id == task_id,
                        TaskResult.employee_id == emp.id
                    )
                )
                task_result = result.scalar_one_or_none()

                emp_info = {
                    "id": emp.id,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "telegram_id": emp.telegram_id,
                    "result": (
                        dict_from_row(task_result)
                        if task_result else None
                    )
                }

                if task_result:
                    if task_result.is_late:
                        late.append(emp_info)
                    else:
                        completed.append(emp_info)
                else:
                    not_completed.append(emp_info)

            stats["branches"].append({
                "id": branch.id,
                "name": branch.name,
                "completed": completed,
                "not_completed": not_completed,
                "late": late
            })

        stats["branches"].sort(
            key=lambda x: (_extract_number(x['name']), x['name'])
        )
        return stats


async def get_all_task_results(task_id: int) -> List[dict]:
    """Vazifaning barcha natijalarini olish"""
    async with get_session() as session:
        result = await session.execute(
            select(
                TaskResult,
                Employee.first_name,
                Employee.last_name,
                Employee.telegram_id,
                Branch.name.label("branch_name"),
            )
            .outerjoin(
                Employee,
                TaskResult.employee_id == Employee.id,
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .where(TaskResult.task_id == task_id)
            .order_by(TaskResult.submitted_at.asc())
        )

        rows = result.all()
        results = []
        for (
            task_result, first_name, last_name,
            telegram_id, branch_name,
        ) in rows:
            result_dict = dict_from_row(task_result)
            result_dict["first_name"] = (
                first_name or "Noma'lum"
            )
            result_dict["last_name"] = last_name or ""
            result_dict["telegram_id"] = telegram_id
            result_dict["branch_name"] = (
                branch_name or "Noma'lum"
            )
            results.append(result_dict)

        return results


async def has_branch_completion(task_id: int, branch_id: int, shift: str = 'hammasi') -> bool:
    """Filialda birorta xodim vazifani bajarganligini tekshirish"""
    async with get_session() as session:
        query = (
            select(func.count(TaskResult.id))
            .join(Employee, TaskResult.employee_id == Employee.id)
            .where(
                TaskResult.task_id == task_id,
                Employee.branch_id == branch_id,
                Employee.is_active == True
            )
        )
        if shift != 'hammasi':
            query = query.where(Employee.shift == shift)

        result = await session.execute(query)
        count = result.scalar() or 0
        return count > 0


# ============== NOTIFICATIONS ==============

async def check_notification_sent(
    task_id: int, employee_id: int, notification_type: str
) -> bool:
    """Bildirishnoma yuborilganligini tekshirish"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(SentNotification.id).where(
                    SentNotification.task_id == task_id,
                    SentNotification.employee_id == employee_id,
                    SentNotification.notification_type
                    == notification_type
                )
            )
            return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"check_notification_sent error: {e}")
        return False


async def mark_notification_sent(
    task_id: int, employee_id: int, notification_type: str
) -> bool:
    """Bildirishnoma yuborilganligini belgilash"""
    try:
        async with get_session() as session:
            # Avval mavjudligini tekshirish (UNIQUE constraint)
            result = await session.execute(
                select(SentNotification.id).where(
                    SentNotification.task_id == task_id,
                    SentNotification.employee_id == employee_id,
                    SentNotification.notification_type
                    == notification_type
                )
            )
            if result.scalar_one_or_none() is not None:
                return True  # Allaqachon belgilangan

            notification = SentNotification(
                task_id=task_id,
                employee_id=employee_id,
                notification_type=notification_type
            )
            session.add(notification)
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"mark_notification_sent error: {e}")
        return False


async def get_task_result_by_id(result_id: int) -> Optional[dict]:
    """Natija ID orqali natijani olish (barcha ma'lumotlar bilan)"""
    async with get_session() as session:
        result = await session.execute(
            select(
                TaskResult,
                Employee.first_name,
                Employee.last_name,
                Branch.name.label("branch_name"),
                Task.title.label("task_title"),
                Task.id.label("task_id_ref"),
            )
            .outerjoin(
                Employee,
                TaskResult.employee_id == Employee.id,
            )
            .outerjoin(
                Branch, Employee.branch_id == Branch.id
            )
            .outerjoin(
                Task, TaskResult.task_id == Task.id
            )
            .where(TaskResult.id == result_id)
        )
        row = result.first()
        if not row:
            return None

        result_dict = dict_from_row(row[0])
        result_dict["first_name"] = row[1] or "Noma'lum"
        result_dict["last_name"] = row[2] or ""
        result_dict["branch_name"] = row[3] or "Noma'lum"
        result_dict["title"] = row[4] or "Noma'lum"
        result_dict["task_id"] = row[5]
        return result_dict


async def clear_task_notifications(task_id: int) -> bool:
    """Vazifa bildirishnomalarini tozalash"""
    try:
        async with get_session() as session:
            await session.execute(
                delete(SentNotification)
                .where(SentNotification.task_id == task_id)
            )
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"clear_task_notifications error: {e}")
        return False


async def clear_all_notifications() -> bool:
    """Barcha bildirishnomalarni tozalash (kunlik qayta tiklash uchun)"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(func.count(SentNotification.id))
            )
            count = result.scalar() or 0
            
            await session.execute(delete(SentNotification))
            await session.commit()
            logger.info(f"✅ {count} ta bildirishnoma tozalandi")
            return True
    except Exception as e:
        logger.error(f"clear_all_notifications error: {e}")
        return False


async def clear_all_task_results() -> bool:
    """Barcha vazifa natijalarini tozalash (kunlik qayta tiklash uchun)"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(func.count(TaskResult.id))
            )
            count = result.scalar() or 0
            
            await session.execute(delete(TaskResult))
            await session.commit()
            logger.info(f"✅ {count} ta vazifa natijasi tozalandi")
            return True
    except Exception as e:
        logger.error(f"clear_all_task_results error: {e}")
        return False


async def clear_all_used_photos() -> bool:
    """Barcha ishlatilgan rasmlarni tozalash (kunlik qayta tiklash uchun)"""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(func.count(UsedPhoto.id))
            )
            count = result.scalar() or 0
            
            await session.execute(delete(UsedPhoto))
            await session.commit()
            logger.info(f"✅ {count} ta ishlatilgan rasm tozalandi")
            return True
    except Exception as e:
        logger.error(f"clear_all_used_photos error: {e}")
        return False