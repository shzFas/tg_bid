from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..texts import ASK_DESC
from ..keyboards import nav_kb

router = Router()

@router.message(RequestForm.City, F.text)
async def got_city(m: Message, state: FSMContext):
    await state.update_data(city=m.text.strip())
    await state.set_state(RequestForm.Description)
    await m.answer(ASK_DESC, reply_markup=nav_kb())

def register_city_handlers(dp):
    dp.include_router(router)
