from aiogram.fsm.state import StatesGroup, State


class NewSpecForm(StatesGroup):
    WaitingForTgId = State()
    ChoosingCategories = State()
