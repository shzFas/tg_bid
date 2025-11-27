import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .config import settings
from .db import init_db
from .handlers import register_all_handlers

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(
        token=settings.BOT2_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()
    register_all_handlers(dp)

    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logging.info(f"DM Bot started as @{me.username} ({me.id})")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
