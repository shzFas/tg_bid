from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..keyboards import nav_kb
from ..texts import ASK_CATEGORY

router = Router()

async def ask_name(m: Message, state: FSMContext):
    await state.set_state(RequestForm.Name)
    await m.answer("Введите имя:", reply_markup=nav_kb())

@router.message(RequestForm.Name)
async def got_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(RequestForm.Category)
    await m.answer(ASK_CATEGORY)

def register_name_handlers(dp):
    dp.include_router(router)
