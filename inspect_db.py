import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.db_postgres import get_session, Task
from sqlalchemy import select
from utils import helpers

async def main():
    print(f"Server time (helpers.now()): {helpers.now()}")
    async with get_session() as session:
        result = await session.execute(
            select(Task).order_by(Task.id.desc()).limit(3)
        )
        tasks = result.scalars().all()
        for t in tasks:
            print(f"Task ID: {t.id} | Title: {t.title}")
            print(f"  Start time: {t.start_time}")
            print(f"  Deadline:   {t.deadline}")
            print(f"  is_late if submitted now: {helpers.now() > t.deadline}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
