from handlers.admin import router as admin_router
from handlers.employee import router as employee_router
from handlers import registration
from handlers import admin_tasks
from handlers import user

__all__ = ['admin_router', 'employee_router', 'registration', 'admin_tasks', 'user']