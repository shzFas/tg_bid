from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from ..db import set_status_canceled, get_request_by_message_id, get_pool
from ..config import CATEGORY_TO_CHANNEL, CATEGORY_H
from ..keyboards import claim_kb

router = Router()

cancel_state: dict[int, dict] = {}


@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(c: CallbackQuery):
    message_id = int(c.data.split(":")[1])
    cancel_state[c.from_user.id] = {
        "request_id": message_id,
        "dm_message_id": c.message.message_id,
    }
    await c.message.answer("📝 Напишите причину отмены заявки:")
    await c.answer()


@router.message(F.text & (~F.text.startswith("/")))
async def handle_cancel_comment(m: Message):
    user_id = m.from_user.id
    if user_id not in cancel_state:
        return

    info = cancel_state.pop(user_id)
    old_msg_id = info["request_id"]
    dm_message_id = info["dm_message_id"]
    comment = m.text.strip()

    await set_status_canceled(old_msg_id, comment)

    req = await get_request_by_message_id(old_msg_id)
    if not req:
        await m.answer("❌ Заявка не найдена в базе.")
        return

    category = req["category"]
    category_h = CATEGORY_H.get(category, category)
    channel_id = CATEGORY_TO_CHANNEL[category]

    text_back = (
        "🔄 <b>Заявка снова доступна:</b>\n\n"
        f"💬 <b>Комментарий специалиста:</b>\n<i>{comment}</i>\n\n"
        f"👤 {req['name']} | {category_h}\n"
        f"🏙️ {req['city']}\n"
        f"📝 {req['description']}\n"
        f"🕒 {req['created_at']}"
    )

    new_msg = await m.bot.send_message(
        chat_id=channel_id,
        text=text_back,
        reply_markup=claim_kb(),
    )

    async with (await get_pool()).acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET message_id = $1,
                status = 'PENDING',
                claimer_user_id = NULL,
                claimer_username = NULL
            WHERE message_id = $2;
            """,
            new_msg.message_id,
            old_msg_id,
        )

    try:
        await m.bot.delete_message(chat_id=m.chat.id, message_id=dm_message_id)
    except:
        pass

    await m.answer("❌ Заявка отменена и возвращена в общий канал.")

def register_cancel_handlers(dp):
    dp.include_router(router)
