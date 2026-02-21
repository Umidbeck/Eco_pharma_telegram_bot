import asyncio
import os
import sys
from datetime import datetime

# Environment loaded manually in run_command

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.helpers import now
from config import TIMEZONE

print(f"TIMEZONE is {TIMEZONE}")
print(f"helpers.now() returns {now()}, type: {type(now())}")

deadline_str = "2026-02-22 16:00:00"
deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")

print(f"Parsed deadline: {deadline}, type: {type(deadline)}")
print(f"helpers.now() > deadline: {now() > deadline}")

# Check asyncpg integration
async def test_db():
    from database import db
    from database.db_postgres import get_session, Task
    from sqlalchemy import select
    
    # Just check if we can connect to pg
    try:
        async with get_session() as session:
            result = await session.execute(select(Task.deadline).limit(1))
            deadline_db = result.scalar_one_or_none()
            print(f"DB format for deadline: {deadline_db}, has tzinfo: {deadline_db.tzinfo}")
    except Exception as e:
        print(f"DB Error: {e}")

asyncio.run(test_db())
