from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ..states import NewSpecForm
from ..db import get_specialist_with_categories
from ..utils.common import is_admin

router = Router()

@router.callback_query(F.data.startswith("spec_edit:"))
async def spec_edit_cb(c: CallbackQuery, state: FSMContext):
    tg_id = int(c.data.split(":")[1])
    spec = await get_specialist_with_categories(tg_id)

    await state.clear()
    await state.update_data(mode="edit", tg_id=tg_id)
    await state.update_data(full_name=spec["full_name"], username=spec["username"])
    await state.set_state(NewSpecForm.WaitingForFullName)

    await c.message.edit_text(f"✏️ Редактирование:\n<b>{spec['full_name']}</b>\nВведите новое ФИО:")
    await c.answer()


def register_edit_handlers(dp):
    dp.include_router(router)
