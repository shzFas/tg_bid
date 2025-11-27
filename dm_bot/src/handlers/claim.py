from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramForbiddenError

from ..config import settings
from ..db import get_request_by_message_id, set_status_in_progress

router = Router()


@router.callback_query(F.data == "req:claim")
async def claim_request(c: CallbackQuery):
    msg_id = c.message.message_id

    # Всегда грузим заявку из БД по текущему message_id
    req = await get_request_by_message_id(msg_id)
    if not req:
        return await c.answer(
            "Заявка не найдена или изменена (message_id).",
            show_alert=True,
        )

    user = c.from_user
    uname = user.username or user.full_name or str(user.id)

    # Уже в работе у другого
    if req.get("claimer_user_id") and req["claimer_user_id"] != user.id:
        return await c.answer(
            f"Заявка уже у @{req['claimer_username']}.",
            show_alert=True,
        )

    # Помечаем как «в работе»
    await set_status_in_progress(msg_id, user.id, uname)

    # Отправляем карточку самому специалисту (этот же бот)
    try:
        await c.bot.send_message(
            chat_id=user.id,
            text=(
                "🆕 <b>Вы приняли заявку!</b>\n\n"
                f"👤 Имя: {req['name']}\n"
                f"📞 Телефон: <code>{req['phone']}</code>\n"
                f"🏙 Город: {req['city']}\n"
                f"📚 Категория: {req['category']}\n"
                f"📝 {req['description']}"
            ),
            parse_mode="HTML",
        )
    except TelegramForbiddenError:
        return await c.answer(
            "Я не могу написать вам в личку. Разблокируйте бота и нажмите /start.",
            show_alert=True,
        )

    # Красим сообщение в канале
    try:
        await c.message.edit_text(
            f"✅ Заявка принята @{uname}\n\n{c.message.text}"
        )
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await c.answer("Заявка отправлена вам в ЛС.")


def register_claim_handlers(dp):
    dp.include_router(router)
