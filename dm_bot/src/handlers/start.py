from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..config import settings
from ..crypto import verify_short_token
from ..db import get_request_by_message_id, set_status_in_progress
from ..services.request_service import fmt_payload, task_kb

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    token = m.text.split(" ", 1)[1].strip() if " " in m.text else None

    if not token:
        return await m.answer("Используйте кнопку в канале, чтобы получить заявку.")

    message_id = verify_short_token(token, settings.SHARED_SECRET)
    if not message_id:
        return await m.answer("❌ Неверный или просроченный токен")

    req = await get_request_by_message_id(message_id)
    if not req:
        return await m.answer("❌ Заявка не найдена")

    if req["claimer_user_id"] not in [None, m.from_user.id]:
        return await m.answer("⚠ Заявка уже в работе у другого специалиста")

    await set_status_in_progress(
        message_id=message_id,
        user_id=m.from_user.id,
        username=m.from_user.username or m.from_user.full_name
    )

    text = fmt_payload(req)
    kb = task_kb(message_id)
    await m.answer(text, reply_markup=kb)


def register_start_handlers(dp):
    dp.include_router(router)
