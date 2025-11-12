import asyncio, logging
import redis.asyncio as redis

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message

from .config import settings
from .texts import *
from .crypto import verify_short_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()
r: redis.Redis | None = None

@router.message(CommandStart())
async def start(m: Message):
    token = None
    if m.text and " " in m.text:
        token = m.text.split(" ", 1)[1].strip()

    if not token:
        await m.answer(WELCOME); return

    msg_id = verify_short_token(token, settings.SHARED_SECRET)
    if not msg_id:
        await m.answer(INVALID_OR_EXPIRED); return

    # читаем полезную нагрузку из Redis
    key = f"claim:{msg_id}"
    payload = await r.hgetall(key)
    if not payload:
        await m.answer(NOT_FOUND); return

    # проверяем, что именно этот пользователь принял заявку
    claimer_id = await r.get(f"claim:{msg_id}:cid")
    if claimer_id and str(claimer_id) != str(m.from_user.id):
        await m.answer(NOT_YOU); return

    text = (
        f"{DELIVERED_PREFIX}\n"
        f"👤 Имя: {payload.get('name')}\n"
        f"📞 Телефон: {payload.get('phone')}\n"
        f"⚖️ Категория: {payload.get('category_h')}\n"
        f"🏙️ Город: {payload.get('city')}\n"
        f"📝 {payload.get('description')}\n"
        f"🕒 {payload.get('created_at')}"
    )
    await m.answer(text)

async def main():
    global r
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)

    bot = Bot(token=settings.BOT2_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logging.info(f"DM Bot started as @{me.username} ({me.id})")

    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
