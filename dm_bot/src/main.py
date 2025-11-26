import asyncio
import logging
from typing import Dict, List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from .config import settings
from .texts import *
from .crypto import verify_short_token
from .db import (
    init_db,
    get_pool,
    set_status_in_progress,
    set_status_done,
    set_status_canceled,
    reset_to_pending,
    list_claims_for_user,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()

# Глобальное временное состояние: user_id -> message_id
cancel_state: Dict[int, int] = {}


# ----------------------------------------------------
# Форматирование карточки заявки
# ----------------------------------------------------

def fmt_payload(row: Dict) -> str:
    try:
        from .texts import CATEGORY_H
        category_h = CATEGORY_H.get(row["category"], row["category"])
    except Exception:
        category_h = row["category"]

    return (
        f"{DELIVERED_PREFIX}\n"
        f"👤 Имя: {row['name']}\n"
        f"📞 Телефон: {row['phone']}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {row['city']}\n"
        f"📝 {row['description']}\n"
        f"🕒 {row['created_at']}"
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
# /start
# ----------------------------------------------------

@router.message(CommandStart())
async def start(m: Message):
    token = None
    if m.text and " " in m.text:
        token = m.text.split(" ", 1)[1].strip()

    if not token:
        await m.answer(WELCOME + "\n\n" + HELP)
        return

    msg_id = verify_short_token(token, settings.SHARED_SECRET)
    if not msg_id:
        await m.answer(INVALID_OR_EXPIRED)
        return

    async with (await get_pool()).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1",
            msg_id,
        )

    if not row:
        await m.answer(NOT_FOUND)
        return

    data = dict(row)

    # Если заявку уже взял другой специалист
    if data["claimer_user_id"] and data["claimer_user_id"] != m.from_user.id:
        await m.answer(NOT_YOU)
        return

    # Привязываем специалиста
    if data["claimer_user_id"] is None:
        await set_status_in_progress(
            msg_id,
            m.from_user.id,
            m.from_user.username or m.from_user.full_name or str(m.from_user.id),
        )

    await m.answer(fmt_payload(data), reply_markup=task_kb(msg_id))


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
# Отменить — запрос комментария
# ----------------------------------------------------

@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(c: CallbackQuery):
    message_id = int(c.data.split(":")[1])

    cancel_state[c.from_user.id] = message_id

    await c.message.answer("📝 Напишите причину отмены заявки:")
    await c.answer()


# ----------------------------------------------------
# Отмена — приём комментария
# ----------------------------------------------------

@router.message(F.text & (~F.text.startswith("/")))
async def handle_cancel_comment(m: Message):
    user_id = m.from_user.id

    # Если пользователь не в состоянии отмены → пропускаем
    if user_id not in cancel_state:
        return

    message_id = cancel_state[user_id]
    comment = m.text.strip()

    # 1. Ставим статус CANCELED + коммент
    await set_status_canceled(message_id, comment)

    # 2. Ставим статус обратно в PENDING
    await reset_to_pending(message_id)

    # 3. Загружаем заявку из БД
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1;",
            message_id
        )

    if not row:
        await m.answer("❌ Ошибка: заявка не найдена.")
        del cancel_state[user_id]
        return

    data = dict(row)

    # Категория для публикации в правильный канал
    try:
        from .texts import CATEGORY_H
        category_h = CATEGORY_H.get(data["category"], data["category"])
    except:
        category_h = data["category"]

    # 4. Формируем текст для канала
    text_back = (
        "🔄 <b>Заявка снова доступна</b>\n\n"
        f"💬 <b>Комментарий специалиста:</b>\n<i>{comment}</i>\n\n"
        f"👤 {data['name']}\n"
        f"📞 {data['phone']}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {data['city']}\n"
        f"📝 {data['description']}\n"
        f"🕒 {data['created_at']}"
    )

    # 5. Публикуем обратно в канал категории
    try:
        from .config import CATEGORY_TO_CHANNEL
        channel_id = CATEGORY_TO_CHANNEL[data["category"]]

        await m.bot.send_message(
            chat_id=channel_id,
            text=text_back
        )
    except Exception as e:
        await m.answer(f"Ошибка при публикации в канал: {e}")

    # 6. Сообщение пользователю
    await m.answer("❌ Заявка отменена и возвращена в общий канал.")

    # 7. Удаляем кнопки на предыдущем сообщении (чтобы нельзя было нажать «Готово»)
    try:
        await m.bot.edit_message_reply_markup(
            chat_id=m.chat.id,
            message_id=m.message_id - 1,  # предыдущее сообщение — карточка заявки
            reply_markup=None
        )
    except:
        pass

    # 8. Удаляем состояние
    del cancel_state[user_id]


# ----------------------------------------------------
# /tasks
# ----------------------------------------------------

@router.message(Command("tasks"))
async def tasks(m: Message):
    claims = await list_claims_for_user(m.from_user.id, limit=50)

    if not claims:
        await m.answer("У вас нет активных заявок.")
        return

    lines = ["<b>📋 Ваши активные заявки:</b>\n"]

    for r in claims:
        try:
            from .texts import CATEGORY_H
            category_h = CATEGORY_H.get(r["category"], r["category"])
        except Exception:
            category_h = r["category"]

        lines.append(
            f"🔹 <b>#{r['message_id']}</b>\n"
            f"👤 {r['name']}\n"
            f"📞 {r['phone']}\n"
            f"🏙️ {r['city']}\n"
            f"⚖️ Категория: {category_h}\n"
            f"📝 {r['description']}\n"
            f"------------------------------"
        )

    await m.answer("\n".join(lines))


# ----------------------------------------------------
# /help
# ----------------------------------------------------

@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP)


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
