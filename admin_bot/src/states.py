from aiogram.fsm.state import StatesGroup, State

class NewSpecForm(StatesGroup):
    WaitingForTgId = State()
    WaitingForFullName = State()
    ChoosingCategories = State()

class EditRequestState(StatesGroup):
    wait_desc = State()
    wait_phone = State()
    wait_city = State()
    wait_cat = State()
