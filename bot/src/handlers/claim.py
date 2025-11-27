from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from ..config import settings
from ..db import get_request_by_message_id, set_status_in_progress

router = Router()
active_requests: dict[int, dict] = {}


@router.callback_query(F.data == "req:claim")
async def claim_request(c: CallbackQuery):
    msg_id = c.message.message_id

    # 1) берем из кэша
    req = active_requests.get(msg_id)

    # 2) если нет — берем из БД
    if not req:
        db_req = await get_request_by_message_id(msg_id)
        if not db_req:
            return await c.answer("Заявка не найдена или устарела.", show_alert=True)

        # гарантируем единый формат заявки
        req = {
            "category": db_req["category"],
            "name": db_req["name"],
            "phone": db_req["phone"],
            "city": db_req["city"],
            "description": db_req["description"],
            "user_id": db_req.get("claimer_user_id"),
            "username": db_req.get("claimer_username"),
        }
        active_requests[msg_id] = req

    # гарантируем наличие user_id и username
    req.setdefault("user_id", None)
    req.setdefault("username", None)

    user = c.from_user
    uname = user.username or user.full_name

    # если заявка уже принята – не даём взять
    if req["user_id"]:
        if req["user_id"] == user.id:
            return await c.answer("Вы уже приняли эту заявку.")
        return await c.answer(f"Заявку уже взял @{req['username']}.", show_alert=True)

    # принять заявку
    req["user_id"] = user.id
    req["username"] = uname
    await set_status_in_progress(msg_id, user.id, uname)

    # 📥 Текст для dm_bot – полный пакет
    text_for_dm = (
        "🆕 <b>Вы приняли заявку!</b>\n\n"
        f"👤 <b>Имя:</b> {req['name']}\n"
        f"📞 <b>Телефон:</b> <code>{req['phone']}</code>\n"
        f"🏙 <b>Город:</b> {req['city']}\n"
        f"📚 <b>Категория:</b> {req['category']}\n"
        f"📝 <b>Описание:</b> {req['description']}"
    )

    # отправка в ЛС через dm_bot
    dm_bot = Bot(
        token=settings.BOT2_TOKEN, 
        default=DefaultBotProperties(parse_mode="HTML")
    )

    try:
        await dm_bot.send_message(user.id, text_for_dm)
    except TelegramForbiddenError:
        return await c.answer(
            f"Открой @{settings.BOT2_USERNAME} и нажми /start!",
            show_alert=True
        )
    finally:
        await dm_bot.session.close()

    # Обновляем сообщение в канале
    try:
        await c.message.edit_text(
            f"✅ Заявка принята @{uname}\n\n{c.message.text}"
        )
        await c.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    await c.answer("Заявка принята.")
    
def register_claim_handlers(dp):
    dp.include_router(router)
