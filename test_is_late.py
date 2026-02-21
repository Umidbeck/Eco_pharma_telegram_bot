import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import helpers
from config import TIMEZONE
from database.db_postgres import (
    get_session, create_task, submit_task_result_by_telegram_id, TaskResult,
    get_task, create_employee, get_employee_by_telegram_id
)
from database import db

# Use SQLite for quick test if postgres is not available
os.environ["DATABASE_TYPE"] = "sqlite"

async def run_test():
    # Insert mock employee
    try:
        await db.create_employee(
            telegram_id=999999999,
            first_name="Test",
            last_name="User",
            branch_id=1,
            shift="kunduzgi"
        )
    except Exception as e:
        pass # might already exist
    
    # Create task with deadline +1 hour
    start_time = helpers.now()
    deadline = start_time + timedelta(hours=1)
    
    # insert dummy branch
    async with db.get_db() as db_conn:
        await db_conn.execute("INSERT OR IGNORE INTO branches (id, name, address) VALUES (1, 'Test Branch', 'Test Address')")
        await db_conn.commit()

    task_id = await db.create_task(
        title="Test Task",
        description="Testing is_late",
        task_type="bir_martalik",
        result_type="matn",
        shift="hammasi",
        start_time=start_time,
        deadline=deadline,
        branch_ids=[1]
    )
    
    # Submit task result
    result_id, position, is_late = await db.submit_task_result_by_telegram_id(
        task_id=task_id,
        telegram_id=999999999,
        result_text="Bajarildi!"
    )
    
    print(f"Task deadline: {deadline}")
    print(f"Current time: {helpers.now()}")
    print(f"Is late? {is_late}")
    assert not is_late

if __name__ == "__main__":
    asyncio.run(run_test())
