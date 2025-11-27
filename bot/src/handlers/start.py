from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..texts import HELLO, ASK_PHONE
from ..keyboards import phone_kb, nav_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RequestForm.Phone)
    await m.answer(HELLO, reply_markup=phone_kb())
    await m.answer(ASK_PHONE, reply_markup=nav_kb())

def register_start_handlers(dp):
    dp.include_router(router)
