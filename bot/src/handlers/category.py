from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..texts import ASK_CITY, ASK_CATEGORY
from ..keyboards import nav_kb, categories_kb

router = Router()


@router.callback_query(RequestForm.Category, F.data.startswith("cat:"))
async def choose_category(c: CallbackQuery, state: FSMContext):
    _, cat = c.data.split(":", 1)
    await state.update_data(category=cat)
    await state.set_state(RequestForm.City)
    await c.message.edit_text(ASK_CITY, reply_markup=nav_kb())
    await c.answer()


@router.message(RequestForm.Category)
async def must_click_category(m: Message):
    await m.answer("Выберите категорию кнопкой ниже 👇", reply_markup=categories_kb())


def register_category_handlers(dp):
    dp.include_router(router)
