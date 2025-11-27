from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..texts import ASK_NAME
from ..keyboards import nav_kb
from .name import ask_name

router = Router()

@router.message(RequestForm.Phone, F.contact)
async def got_contact(m: Message, state: FSMContext):
    phone = m.contact.phone_number
    await state.update_data(phone=phone)
    await ask_name(m, state)

@router.message(RequestForm.Phone, F.text)
async def phone_text(m: Message, state: FSMContext):
    txt = m.text.strip()
    if len(txt) < 6:
        await m.answer("Похоже, это не номер. Введите снова.", reply_markup=nav_kb())
        return

    await state.update_data(phone=txt)
    await ask_name(m, state)

def register_phone_handlers(dp):
    dp.include_router(router)
