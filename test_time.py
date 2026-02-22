import asyncio
from datetime import datetime
import pytz
import database.db_postgres as db

async def test():
    await db.init_db()
    async with db.get_session() as session:
        result = await session.execute(db.select(db.Task).order_by(db.Task.id.desc()).limit(1))
        task = result.scalar_one_or_none()
        if not task:
            print("No task")
            return
        
        deadline = task.deadline
        print(f"Type of deadline from DB: {type(deadline)}")
        print(f"Deadline from DB: {deadline}")
        
        now = db._tashkent_now()
        print(f"Now: {now}")
        print(f"Is Late: {now > deadline}")
        if hasattr(deadline, 'tzinfo'):
            print(f"TZ Info: {deadline.tzinfo}")
        
if __name__ == "__main__":
    asyncio.run(test())
