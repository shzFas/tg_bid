from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ..db import set_specialist_categories, get_specialist_with_categories
from ..keyboards import categories_kb

router = Router()

@router.callback_query(F.data.startswith("spec_cat:open:"))
async def spec_cat_open(c: CallbackQuery, state: FSMContext):
    tg_id = int(c.data.split(":")[2])
    spec = await get_specialist_with_categories(tg_id)

    await state.clear()
    await state.update_data(tg_id=tg_id, categories=spec["categories"])
    await c.message.edit_text("📚 Редактирование категорий", reply_markup=categories_kb(spec["categories"], mode="edit"))
    await c.answer()

@router.callback_query(F.data == "spec_cat:save")
async def spec_cat_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    categories = data["categories"]

    await set_specialist_categories(tg_id, categories)
    await state.clear()

    await c.message.edit_text(f"Обновлено: {', '.join(categories)}")
    await c.answer()


def register_categories_handlers(dp):
    dp.include_router(router)
