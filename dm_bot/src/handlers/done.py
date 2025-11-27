from aiogram import Router, F
from aiogram.types import CallbackQuery
from ..db import set_status_done

router = Router()

@router.callback_query(F.data.startswith("done:"))
async def cb_done(c: CallbackQuery):
    message_id = int(c.data.split(":")[1])
    await set_status_done(message_id)
    await c.message.edit_text("✔ Заявка завершена")
    await c.answer()

def register_done_handlers(dp):
    dp.include_router(router)
