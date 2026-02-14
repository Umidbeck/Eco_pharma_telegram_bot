from aiogram.fsm.state import State, StatesGroup  # <-- BU TO'G'RI IMPORT!


class AdminStates(StatesGroup):
    add_branch = State()

    add_employee_tid = State()
    add_employee_first = State()
    add_employee_last = State()
    add_employee_phone = State()
    add_employee_branch = State()
    add_employee_shift = State()

    create_task_name = State()
    create_task_desc = State()
    create_task_branch = State()
    create_task_shift = State()
    create_task_media = State()
    create_task_deadline = State()


class CompleteTask(StatesGroup):
    waiting_media = State()