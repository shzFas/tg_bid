from aiogram.fsm.state import State, StatesGroup

class SpecReg(StatesGroup):
    name = State()
    phone = State()
    specialization = State()

class CancelNote(StatesGroup):
    note = State()