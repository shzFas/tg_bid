import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .config import settings
from .db import init_db, add_specialist, set_specialist_categories, get_specialists_list

logging.basicConfig(level=logging.INFO)
router = Router()


def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list


@router.message(Command("start"))
async def start(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(
        "🔐 Админ–бот\n\n"
        "/add_spec <tg_id> [username]  – добавить/обновить специалиста\n"
        "/set_cats <tg_id> ACCOUNTING,LAW… – категории\n"
        "/list_specs – список специалистов\n"
    )


@router.message(Command("add_spec"))
async def add_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return
    if not command.args:
        await m.answer("Использование: /add_spec <tg_id> [username]")
        return

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except:
        return await m.answer("tg_id должен быть числом")

    username = parts[1].lstrip("@") if len(parts) == 2 else None
    spec = await add_specialist(tg_id, username)
    await m.answer(f"OK: {spec}")


@router.message(Command("set_cats"))
async def set_cats(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("/set_cats <tg_id> ACCOUNTING,LAW,EGOV")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except:
        return await m.answer("tg_id должен быть числом")

    if len(parts) == 1:
        return await m.answer("Нужно указать категории")

    raw_cats = parts[1].split(",")
    cats = [c.strip().upper() for c in raw_cats]
    allowed = {"ACCOUNTING", "LAW", "EGOV"}

    if any(c not in allowed for c in cats):
        return await m.answer(f"Допустимые категории: {allowed}")

    await set_specialist_categories(tg_id, cats)
    await m.answer("Категории обновлены")


@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()
    if not specs:
        return await m.answer("Пока нет специалистов")

    lines = []
    for s in specs:
        lines.append(
            f"ID={s['id']} tg={s['tg_user_id']} @{s['username']}\n"
            f"cats: {', '.join(s['categories'] or [])}\n"
            f"------------------------"
        )

    await m.answer("\n".join(lines))


async def main():
    await init_db()

    bot = Bot(
        token=settings.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
