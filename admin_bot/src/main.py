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


HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/add_spec tg_id username</code>\n"
    "<code>/set_cats tg_id ACCOUNTING,LAW,EGOV</code>\n"
    "<code>/list_specs</code>\n\n"
    "<b>📂 Работа с заявками:</b>\n"
    "<code>/req id</code>\n"
    "<code>/set_phone id номер</code>\n"
    "<code>/set_city id город</code>\n"
    "<code>/set_desc id текст</code>\n\n"
    "<b>📤 Excel экспорт:</b>\n"
    "<code>/export</code>\n"
)

@router.message(Command("start"))
async def start(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT)

@router.message(Command("help"))
async def help_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT)


@router.message(Command("add_spec"))
async def add_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return
    if not command.args:
        await m.answer("<code>Использование: /add_spec tg_id username</code>")
        return

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except:
        return await m.answer("<code>tg_id должен быть числом</code>")

    username = parts[1].lstrip("@") if len(parts) == 2 else None
    spec = await add_specialist(tg_id, username)
    await m.answer(f"<b>OK:</b>\n<code>{spec}</code>")


@router.message(Command("set_cats"))
async def set_cats(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>/set_cats tg_id ACCOUNTING,LAW,EGOV</code>")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except:
        return await m.answer("<code>tg_id должен быть числом</code>")

    if len(parts) == 1:
        return await m.answer("<code>Нужно указать категории</code>")

    raw_cats = parts[1].split(",")
    cats = [c.strip().upper() for c in raw_cats]
    allowed = {"ACCOUNTING", "LAW", "EGOV"}

    if any(c not in allowed for c in cats):
        return await m.answer(f"<code>Допустимые категории: {allowed}</code>")

    await set_specialist_categories(tg_id, cats)
    await m.answer("<b>Категории обновлены.</b>")


@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()
    if not specs:
        return await m.answer("<code>Пока нет специалистов</code>")

    lines = []
    for s in specs:
        categories = ", ".join(s['categories'] or [])
        lines.append(
            f"ID={s['id']} tg={s['tg_user_id']} @{s.get('username')}\n"
            f"cats: {categories}\n"
            f"------------------------"
        )

    await m.answer("<code>" + "\n".join(lines) + "</code>")



async def main():
    await init_db()

    bot = Bot(
        token=settings.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),  # можно оставить
    )
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
