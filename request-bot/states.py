from aiogram.fsm.state import State, StatesGroup

class RequestForm(StatesGroup):
    phone = State()
    name = State()
    city = State()
    description = State()
    specialization = State()  # category
