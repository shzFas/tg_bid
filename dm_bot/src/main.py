import asyncio
import logging
import hmac
import hashlib
from typing import Dict, List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from .config import settings, CATEGORY_TO_CHANNEL, CATEGORY_H
from .crypto import verify_short_token
from .db import (
    init_db,
    get_pool,
    get_request_by_message_id,
    set_status_in_progress,
    set_status_done,
    set_status_canceled,
    reset_to_pending,
    list_claims_for_user,
)
from .keyboards import claim_kb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()

# user_id → {request_id, dm_message_id}
cancel_state: Dict[int, Dict] = {}

# msg_id → cached request info (если понадобится)
active_requests: dict[int, dict] = {}


# ----------------------------------------------------
# TOKEN (для старого механизма, можно оставить на будущее)
# ----------------------------------------------------

def make_short_token(message_id: int) -> str:
    mid_hex = format(message_id, "x")
    sig = hmac.new(
        settings.SHARED_SECRET.encode(),
        mid_hex.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{mid_hex}.{sig}"


# ----------------------------------------------------
# Форматирование карточки заявки
# ----------------------------------------------------

def fmt_payload(row: Dict) -> str:
    category_h = CATEGORY_H.get(row["category"], row["category"])
    return (
        f"📄 <b>Заявка клиента:</b>\n\n"
        f"👤 Имя: {row['name']}\n"
        f"📞 Телефон: {row['phone']}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {row['city']}\n"
        f"📝 {row['description']}\n"
        f"🕒 {row['created_at']}\n\n"
        f"Теперь вы можете связаться с клиентом и вести работу по этой заявке."
    )


def task_kb(message_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{message_id}"),
                InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{message_id}"),
            ]
        ]
    )


# ----------------------------------------------------
# /start <token>
# ----------------------------------------------------

@router.message(CommandStart())
async def start(m: Message):
    token = m.text.split(" ", 1)[1].strip() if " " in m.text else None

    if not token:
        await m.answer("Привет! Используйте кнопку в канале, чтобы получить заявку.")
        return

    message_id = verify_short_token(token, settings.SHARED_SECRET)
    if not message_id:
        await m.answer("❌ Токен просрочен или неверен.")
        return

    req = await get_request_by_message_id(message_id)
    if not req:
        await m.answer("❌ Заявка не найдена.")
        return

    # Проверка владельца
    if req["claimer_user_id"] and req["claimer_user_id"] != m.from_user.id:
        await m.answer("Эта заявка уже в работе у другого специалиста.")
        return

    # Присваиваем заявку специалисту
    if req["claimer_user_id"] is None:
        await set_status_in_progress(
            message_id,
            m.from_user.id,
            m.from_user.username or m.from_user.full_name or str(m.from_user.id),
        )

    await m.answer(fmt_payload(req), reply_markup=task_kb(message_id))


# ----------------------------------------------------
# Готово
# ----------------------------------------------------

@router.callback_query(F.data.startswith("done:"))
async def cb_done(c: CallbackQuery):
    message_id = int(c.data.split(":")[1])

    await set_status_done(message_id)
    await c.message.edit_text("✅ Заявка выполнена и отправлена в архив.")
    await c.answer()


# ----------------------------------------------------
# Отменить → запрос комментария
# ----------------------------------------------------

@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(c: CallbackQuery):
    message_id = int(c.data.split(":")[1])

    cancel_state[c.from_user.id] = {
        "request_id": message_id,
        "dm_message_id": c.message.message_id
    }

    await c.message.answer("📝 Напишите причину отмены заявки:")
    await c.answer()


# ----------------------------------------------------
# Получение комментария
# ----------------------------------------------------

@router.message(F.text & (~F.text.startswith("/")))
async def handle_cancel_comment(m: Message):
    user_id = m.from_user.id
    if user_id not in cancel_state:
        return

    req_info = cancel_state[user_id]
    old_msg_id = req_info["request_id"]
    dm_message_id = req_info["dm_message_id"]
    comment = m.text.strip()

    # Обновляем статус
    await set_status_canceled(old_msg_id, comment)
    await reset_to_pending(old_msg_id)

    # Загружаем заявку
    req = await get_request_by_message_id(old_msg_id)
    if not req:
        await m.answer("❌ Ошибка: заявка не найдена.")
        del cancel_state[user_id]
        return

    category_h = CATEGORY_H.get(req["category"], req["category"])
    channel_id = CATEGORY_TO_CHANNEL[req["category"]]

    # Формируем новое сообщение (как на скрине)
    text_back = (
        "🔄 <b>Заявка снова доступна</b>\n\n"
        f"💬 <b>Комментарий специалиста:</b>\n<i>{comment}</i>\n\n"
        f"👤 {req['name']}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {req['city']}\n"
        f"📝 {req['description']}\n"
        f"🕒 {req['created_at']}"
    )

    # Отправляем новое сообщение в канал
    new_msg = await m.bot.send_message(
        chat_id=channel_id,
        text=text_back,
        reply_markup=claim_kb()
    )

    # Обновляем message_id заявки в БД
    async with (await get_pool()).acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET message_id = $1,
                claimer_user_id = NULL,
                claimer_username = NULL,
                status = 'PENDING'
            WHERE message_id = $2;
            """,
            new_msg.message_id,
            old_msg_id
        )

    # Удаляем карточку задач в ЛС
    try:
        await m.bot.delete_message(
            chat_id=m.chat.id,
            message_id=dm_message_id
        )
    except:
        pass

    await m.answer("❌ Заявка отменена и возвращена в общий канал.")
    del cancel_state[user_id]


# ----------------------------------------------------
# Принять заявку (повторная рассылка с комментарием)
# ----------------------------------------------------

@router.callback_query(F.data == "req:claim")
async def claim_request(c: CallbackQuery):
    msg_id = c.message.message_id

    req = await get_request_by_message_id(msg_id)
    if not req:
        await c.answer("Заявка не найдена или устарела.", show_alert=True)
        return

    # Уже в работе у другого
    if req["claimer_user_id"] and req["claimer_user_id"] != c.from_user.id:
        await c.answer(f"Уже в работе у @{req['claimer_username']}.", show_alert=True)
        return

    uname = c.from_user.username or c.from_user.full_name or str(c.from_user.id)

    # Помечаем как "в работе"
    await set_status_in_progress(msg_id, c.from_user.id, uname)

    # Текст из канала (там уже есть "Заявка снова доступна" и "Комментарий специалиста")
    original_text = c.message.text or ""
    phone = req.get("phone")

    # 🔹 Текст, который уйдёт в ЛС новому специалисту
    lines = [
        "🆕 Вы приняли заявку:",
        "",
        original_text,
        "",
        "Теперь вы можете связаться с клиентом и вести работу по этой заявке.",
    ]

    await c.bot.send_message(
        chat_id=c.from_user.id,
        text="\n".join(lines),
    )

    # 🔹 Обновляем сообщение в канале
    new_text = (
        "✅ Заявка принята в работу\n\n"
        f"{original_text}\n\n"
        f"👨‍💼 Принял: @{uname}"
    )
    try:
        await c.message.edit_text(new_text)
        await c.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    await c.answer("Вы взяли заявку. Подробности отправлены вам в ЛС.")


# ----------------------------------------------------
# /tasks — список активных заявок с кнопками
# ----------------------------------------------------

@router.message(Command("tasks"))
async def tasks(m: Message):
    claims = await list_claims_for_user(m.from_user.id, limit=50)

    if not claims:
        await m.answer("У вас нет активных заявок.")
        return

    await m.answer(
        f"📋 У вас {len(claims)} активных заявок.\n"
        f"Каждая заявка отправлена отдельной карточкой ниже."
    )

    for r in claims:
        text = fmt_payload(r)
        kb = task_kb(r["message_id"])
        await m.answer(text, reply_markup=kb)
        await asyncio.sleep(0.05)  # небольшой анти-флуд


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------

async def main():
    await init_db()

    bot = Bot(
        token=settings.BOT2_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    logging.info(f"DM Bot started as @{me.username} ({me.id})")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
