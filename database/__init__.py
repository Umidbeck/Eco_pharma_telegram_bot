"""
Database module - Auto-selects SQLite or PostgreSQL based on config
"""
import os

# Get database type from environment or config
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    # PostgreSQL with SQLAlchemy
    from database import db_postgres as _db_module
else:
    # SQLite (legacy)
    from database import db as _db_module


class _DBProxy:
    """Proxy class for backward compatibility.
    Allows both `db.func_name()` and direct `func_name()` calls.
    """
    def __getattr__(self, name):
        return getattr(_db_module, name)


db = _DBProxy()

# Direct function exports for `from database import func_name`
init_db = _db_module.init_db
close_db = _db_module.close_db
create_branch = _db_module.create_branch
get_all_branches = _db_module.get_all_branches
get_branch = _db_module.get_branch
update_branch = _db_module.update_branch
delete_branch = _db_module.delete_branch
get_branch_employees_count = _db_module.get_branch_employees_count
create_employee = _db_module.create_employee
get_employee_by_telegram_id = _db_module.get_employee_by_telegram_id
get_employee = _db_module.get_employee
update_employee = _db_module.update_employee
update_employee_by_telegram_id = _db_module.update_employee_by_telegram_id
delete_employee = _db_module.delete_employee
delete_employee_by_telegram_id = _db_module.delete_employee_by_telegram_id
get_all_employees = _db_module.get_all_employees
get_employees_by_branch = _db_module.get_employees_by_branch
get_total_employees_count = _db_module.get_total_employees_count
create_task = _db_module.create_task
get_task = _db_module.get_task
update_task = _db_module.update_task
delete_task = _db_module.delete_task
deactivate_task = _db_module.deactivate_task
get_task_branches = _db_module.get_task_branches
get_active_tasks = _db_module.get_active_tasks
get_employee_tasks = _db_module.get_employee_tasks
get_employee_tasks_by_telegram_id = _db_module.get_employee_tasks_by_telegram_id
get_employees_for_task = _db_module.get_employees_for_task
get_daily_tasks = _db_module.get_daily_tasks
submit_task_result = _db_module.submit_task_result
submit_task_result_by_telegram_id = _db_module.submit_task_result_by_telegram_id
check_photo_used = _db_module.check_photo_used
get_task_result = _db_module.get_task_result
get_task_result_by_telegram_id = _db_module.get_task_result_by_telegram_id
has_submitted_result = _db_module.has_submitted_result
get_task_statistics = _db_module.get_task_statistics
get_all_task_results = _db_module.get_all_task_results
get_task_result_by_id = _db_module.get_task_result_by_id
check_notification_sent = _db_module.check_notification_sent
mark_notification_sent = _db_module.mark_notification_sent
clear_task_notifications = _db_module.clear_task_notifications
clear_all_notifications = _db_module.clear_all_notifications
clear_all_task_results = _db_module.clear_all_task_results
clear_all_used_photos = _db_module.clear_all_used_photos
has_branch_completion = _db_module.has_branch_completion
