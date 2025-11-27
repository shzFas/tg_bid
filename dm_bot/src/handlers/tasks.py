from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import list_claims_for_user
from ..services.request_service import fmt_payload, task_kb

router = Router()

@router.message(Command("tasks"))
async def tasks(m: Message):
    claims = await list_claims_for_user(m.from_user.id)

    if not claims:
        return await m.answer("Нет активных заявок")

    for req in claims:
        await m.answer(fmt_payload(req), reply_markup=task_kb(req["message_id"]))

def register_tasks_handlers(dp):
    dp.include_router(router)
