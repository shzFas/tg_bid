from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError

from ..db import get_specialist_with_categories
from ..config import CATEGORY_TO_CHANNEL
from ..utils.common import is_admin

router = Router()

@router.message(Command("invite_spec"))
async def invite_spec_cmd(m: Message, command):
    if not is_admin(m.from_user.id):
        return

    tg_id = int(command.args)
    spec = await get_specialist_with_categories(tg_id)

    links = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await m.bot.create_chat_invite_link(chat_id)
            links.append(f"{cat}: {link.invite_link}")

    await m.answer("\n".join(links) if links else "❌ Не удалось")


@router.message(Command("notify_spec"))
async def notify_spec_cmd(m: Message, command):
    tg_id = int(command.args)
    spec = await get_specialist_with_categories(tg_id)

    links = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await m.bot.create_chat_invite_link(chat_id)
            links.append(f"{cat}: {link.invite_link}")

    try:
        await m.bot.send_message(tg_id, "\n".join(links))
        await m.answer("Отправлено")
    except TelegramForbiddenError:
        await m.answer("❌ Специалист не открыл бота")


def register_invite_handlers(dp):
    dp.include_router(router)
