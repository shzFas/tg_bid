import asyncio
import logging
from typing import Dict, List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .config import settings
from .texts import *  # WELCOME, HELP, DELIVERED_PREFIX, MY_*, NOT_YOU, ...
from .crypto import verify_short_token
from .db import get_pool, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()


def fmt_payload(row: Dict) -> str:
    # category_h восстанавливаем по коду категории, если есть словарь CATEGORY_H в texts
    try:
        from .texts import CATEGORY_H  # type: ignore
        cat_code = row.get("category")
        category_h = CATEGORY_H.get(cat_code, cat_code)
    except Exception:
        category_h = row.get("category")

    return (
        f"{DELIVERED_PREFIX}\n"
        f"👤 Имя: {row.get('name')}\n"
        f"📞 Телефон: {row.get('phone')}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {row.get('city')}\n"
        f"📝 {row.get('description')}\n"
        f"🕒 {row.get('created_at')}"
    )


async def get_user_claims(user_id: int, limit: int = 20) -> List[Dict]:
    """
    Возвращает заявки, которые принял этот пользователь.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM requests
            WHERE claimer_user_id = $1
            ORDER BY created_at DESC
            LIMIT $2;
            """,
            user_id,
            limit,
        )
        return [dict(r) for r in rows]


@router.message(CommandStart())
async def start(m: Message):
    token = None
    if m.text and " " in m.text:
        token = m.text.split(" ", 1)[1].strip()

    # Если без токена — просто приветствие и /help
    if not token:
        await m.answer(WELCOME + "\n\n" + HELP)
        return

    msg_id = verify_short_token(token, settings.SHARED_SECRET)
    if not msg_id:
        await m.answer(INVALID_OR_EXPIRED)
        return

    # Читаем заявку из PostgreSQL по message_id
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1;",
            msg_id,
        )

    if not row:
        await m.answer(NOT_FOUND)
        return

    data = dict(row)

    # Проверяем, что именно этот пользователь принял заявку
    claimer_id = data.get("claimer_user_id")
    if claimer_id is not None and str(claimer_id) != str(m.from_user.id):
        await m.answer(NOT_YOU)
        return

    # Если в БД ещё не записан claimer_user_id (теоретически),
    # можно привязать её к этому пользователю.
    if claimer_id is None:
        async with (await get_pool()).acquire() as conn:
            await conn.execute(
                """
                UPDATE requests
                SET claimer_user_id = $2,
                    claimer_username = $3
                WHERE message_id = $1;
                """,
                msg_id,
                m.from_user.id,
                m.from_user.username or m.from_user.full_name or str(m.from_user.id),
            )
        data["claimer_user_id"] = m.from_user.id

    # Просто отправляем заявку текстом
    await m.answer(fmt_payload(data))


@router.message(Command(commands={"my", "tasks"}))
async def my_tasks(m: Message):
    claims = await get_user_claims(m.from_user.id, limit=30)
    if not claims:
        await m.answer(MY_EMPTY + "\n\n" + HELP)
        return

    lines = [MY_HEADER]
    for row in claims:
        phone = row.get("phone")
        try:
            from .texts import CATEGORY_H  # type: ignore
            cat_code = row.get("category")
            category_h = CATEGORY_H.get(cat_code, cat_code)
        except Exception:
            category_h = row.get("category")

        lines.append(
            f"{MY_ITEM_BULLET} <b>#{row.get('message_id')}</b>\n"
            f"👤 Имя: {row.get('name')}\n"
            f"📞 Телефон: {phone}\n"
            f"📞 Whatsapp: wa.me/{phone}\n"
            f"⚖️ Категория: {category_h}\n"
            f"🏙️ Город: {row.get('city')}\n"
            f"📝 {row.get('description')}\n"
            f"🕒 {row.get('created_at')}\n"
            f"-------------------------"
        )

    await m.answer("\n".join(lines))


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP)


async def main():
    # Инициализируем БД (idempotent — просто убедится, что таблица есть)
    await init_db()

    bot = Bot(
        token=settings.BOT2_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logging.info(f"DM Bot started as @{me.username} ({me.id})")

    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
