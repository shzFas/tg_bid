from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..utils import preview_text
from ..texts import CONFIRM
from ..keyboards import confirm_kb

router = Router()

@router.message(RequestForm.Description, F.text)
async def got_desc(m: Message, state: FSMContext):
    await state.update_data(description=m.text.strip())
    data = await state.get_data()

    await state.set_state(RequestForm.Confirm)
    preview = preview_text(data)
    await m.answer(CONFIRM.format(preview=preview), reply_markup=confirm_kb())

def register_description_handlers(dp):
    dp.include_router(router)
