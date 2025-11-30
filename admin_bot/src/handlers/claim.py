from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from ..db import get_request_by_message_id, set_status_in_progress
from ..config import settings, CATEGORY_TO_CHANNEL

router = Router()


@router.callback_query(F.data == "req:claim")
async def claim_request(call: CallbackQuery, bot):
    # ID сообщения в КАНАЛЕ
    msg_id = call.message.message_id

    # Ищем заявку по message_id
    req = await get_request_by_message_id(msg_id)
    if not req:
        return await call.answer("❌ Заявка не найдена")

    user = call.from_user
    username = user.username or user.full_name or str(user.id)

    # Если уже занято другим
    if req.get("claimer_user_id") and req["claimer_user_id"] != user.id:
        return await call.answer(
            f"Заявку уже взял @{req['claimer_username']}",
            show_alert=True,
        )

    # 1) ОБНОВЛЯЕМ БАЗУ
    await set_status_in_progress(msg_id, user.id, username)

    # 2) ОТПРАВЛЯЕМ СПЕЦИАЛИСТУ В ЛС (DM-бот)
    dm_bot = Bot(
        token=settings.DM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    try:
        await dm_bot.send_message(
            chat_id=user.id,
            text=(
                "🆕 <b>Вы приняли заявку!</b>\n\n"
                f"👤 Имя: {req['name']}\n"
                f"📞 Телефон: <code>{req['phone']}</code>\n"
                f"🏙 Город: {req['city']}\n"
                f"📚 Категория: {req['category']}\n"
                f"📝 {req['description']}"
            ),
        )
    except TelegramForbiddenError:
        return await call.answer(
            f"Открой @{settings.DM_BOT_USERNAME} и нажми /start",
            show_alert=True
        )
    finally:
        await dm_bot.session.close()

    # 3) ОБНОВЛЯЕМ СООБЩЕНИЕ В КАНАЛЕ
    channel_id = CATEGORY_TO_CHANNEL.get(req["category"])
    try:
        # 👉 УДАЛЯЕМ КНОПКУ
        await bot.edit_message_reply_markup(
            chat_id=channel_id,
            message_id=msg_id,
            reply_markup=None
        )

        # 👉 ОБНОВЛЯЕМ ТЕКСТ СООБЩЕНИЯ
        await bot.edit_message_text(
            chat_id=channel_id,
            message_id=msg_id,
            text=(
                f"🟢 Заявка принята @{username}\n\n"
                f"👤 Имя: {req['name']}\n"
                f"🏙 Город: {req['city']}\n"
                f"💬 Описание:\n{req['description']}"
            ),
        )

    except Exception as e:
        print("Ошибка обновления сообщения в канале:", e)

    await call.answer("✔ Заявка передана в работу!")

def register_claim_handlers(dp):
    dp.include_router(router)