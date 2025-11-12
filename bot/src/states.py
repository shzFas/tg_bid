from aiogram.fsm.state import StatesGroup, State

class RequestForm(StatesGroup):
    Phone = State()
    Name = State()
    Category = State()
    City = State()
    Description = State()
    Confirm = State()
