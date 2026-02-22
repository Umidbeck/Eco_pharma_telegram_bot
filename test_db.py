import asyncio
from database.db_postgres import get_session, Task
from sqlalchemy import select

async def main():
    async with get_session() as session:
        result = await session.execute(select(Task).order_by(Task.id.desc()).limit(1))
        task = result.scalar_one_or_none()
        if task:
            print(f"Task ID: {task.id}, title: {task.title}")
            print(f"Start time: {task.start_time} (Type: {type(task.start_time)})")
            print(f"Deadline: {task.deadline} (Type: {type(task.deadline)})")

if __name__ == "__main__":
    asyncio.run(main())
