import asyncio
import logging
from typing import Dict, List, Tuple

import redis.asyncio as redis
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .config import settings
from .texts import *
from .crypto import verify_short_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()

r: redis.Redis | None = None

def fmt_payload(payload: Dict[str, str]) -> str:
    return (
        f"{DELIVERED_PREFIX}\n"
        f"👤 Имя: {payload.get('name')}\n"
        f"📞 Телефон: {payload.get('phone')}\n"
        f"⚖️ Категория: {payload.get('category_h')}\n"
        f"🏙️ Город: {payload.get('city')}\n"
        f"📝 {payload.get('description')}\n"
        f"🕒 {payload.get('created_at')}"
    )

async def add_to_user_index(user_id: int, msg_id: int) -> None:
    await r.sadd(f"user:{user_id}:claims", msg_id)
    # TTL множества синхронизировать не обязательно, храним долго.

async def ensure_user_index_built(user_id: int) -> int:
    set_key = f"user:{user_id}:claims"
    if await r.scard(set_key) > 0:
        return 0

    # мягкое сканирование Redis (без KEYS *)
    added = 0
    cursor: int = 0
    pattern = "claim:*:cid"
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=500)
        if not keys:
            if cursor == 0:
                break
            continue

        # получаем все cid пачкой
        values = await r.mget(keys)
        for k, v in zip(keys, values):
            if v is None:
                continue
            if str(v) == str(user_id):
                # ключ вида claim:<msg_id>:cid -> нужно вытащить msg_id
                try:
                    msg_id = int(k.split(":", 2)[1])
                except Exception:
                    continue
                await r.sadd(set_key, msg_id)
                added += 1

        if cursor == 0:
            break

    return added

async def get_user_claims(user_id: int, limit: int = 20) -> List[Tuple[int, Dict[str, str]]]:
    set_key = f"user:{user_id}:claims"
    msg_ids = await r.smembers(set_key)
    if not msg_ids:
        # попробуем построить индекс и перечитать
        await ensure_user_index_built(user_id)
        msg_ids = await r.smembers(set_key)

    # сортируем по убыванию msg_id (как по времени)
    sorted_ids = sorted((int(x) for x in msg_ids), reverse=True)[:limit]
    result: List[Tuple[int, Dict[str, str]]] = []

    if not sorted_ids:
        return result

    # читаем payload’ы пачкой
    for mid in sorted_ids:
        payload = await r.hgetall(f"claim:{mid}")
        if payload:
            result.append((mid, payload))

    return result

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

    # читаем полезную нагрузку из Redis
    key = f"claim:{msg_id}"
    payload = await r.hgetall(key)
    if not payload:
        await m.answer(NOT_FOUND)
        return

    # проверяем, что именно этот пользователь принял заявку
    claimer_id = await r.get(f"claim:{msg_id}:cid")
    if claimer_id and str(claimer_id) != str(m.from_user.id):
        await m.answer(NOT_YOU)
        return

    # индексируем заявку на пользователя (на будущее для /my)
    await add_to_user_index(m.from_user.id, msg_id)

    await m.answer(fmt_payload(payload))

@router.message(Command(commands={"my", "tasks"}))
async def my_tasks(m: Message):
    claims = await get_user_claims(m.from_user.id, limit=30)
    if not claims:
        await m.answer(MY_EMPTY + "\n\n" + HELP)
        return

    lines = [MY_HEADER]
    for msg_id, payload in claims:
        lines.append(
            f"{MY_ITEM_BULLET} <b>#{msg_id}</b> | "
            f"👤 Имя: {payload.get('name')}\n"
            f"📞 Телефон: {payload.get('phone')}\n"
            f"⚖️ Категория: {payload.get('category_h')}\n"
            f"🏙️ Город: {payload.get('city')}\n"
            f"📝 {payload.get('description')}\n"
            f"🕒 {payload.get('created_at')}"
        )
    lines.append("\nОтправьте /start по кнопке в канале у нужной заявки, чтобы получить её детали ещё раз.")

    await m.answer("\n".join(lines))

@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP)

async def main():
    global r
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)

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
