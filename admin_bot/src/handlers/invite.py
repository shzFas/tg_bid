from aiogram import Router, F
from aiogram.types import CallbackQuery
from ..config import CATEGORY_TO_CHANNEL
from ..db import get_specialist_with_categories

router = Router()

@router.callback_query(F.data.startswith("spec_invite:"))
async def spec_invite_cb(c: CallbackQuery):
    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    links = []

    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            invite_link = await c.bot.create_chat_invite_link(chat_id)
            links.append(f"<b>{cat}</b>: {invite_link.invite_link}")

    if not links:
        return await c.message.edit_text("❌ Нет доступных каналов.")

    text = "🔗 <b>Ссылки на каналы:</b>\n\n" + "\n".join(links)

    await c.message.edit_text(text, parse_mode="HTML")
    await c.answer()
