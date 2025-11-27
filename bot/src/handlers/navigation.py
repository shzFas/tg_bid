from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..texts import ASK_PHONE, ASK_NAME, ASK_CATEGORY, ASK_CITY, ASK_DESC
from ..keyboards import categories_kb, nav_kb

router = Router()

@router.callback_query(F.data == "nav:stop")
async def nav_stop(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("Диалог завершён.")
    await c.answer()

@router.callback_query(F.data == "nav:cancel")
async def nav_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("Операция отменена.")
    await c.answer()

@router.callback_query(F.data == "nav:back")
async def nav_back(c: CallbackQuery, state: FSMContext):
    st = await state.get_state()

    if st == RequestForm.Name.state:
        await state.set_state(RequestForm.Phone)
        await c.message.edit_text(ASK_PHONE)
    elif st == RequestForm.Category.state:
        await state.set_state(RequestForm.Name)
        await c.message.edit_text(ASK_NAME)
    elif st == RequestForm.City.state:
        await state.set_state(RequestForm.Category)
        await c.message.edit_text(ASK_CATEGORY, reply_markup=categories_kb())
    elif st == RequestForm.Description.state:
        await state.set_state(RequestForm.City)
        await c.message.edit_text(ASK_CITY)
    elif st == RequestForm.Confirm.state:
        await state.set_state(RequestForm.Description)
        await c.message.edit_text(ASK_DESC)
    else:
        await c.message.answer("Назад недоступно.")

    await c.answer()

def register_navigation_handlers(dp):
    dp.include_router(router)
