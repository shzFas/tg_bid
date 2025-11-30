from aiogram.fsm.state import State, StatesGroup

class ReqForm(StatesGroup):
    phone = State()
    name = State()
    city = State()
    desc = State()
    category = State()
