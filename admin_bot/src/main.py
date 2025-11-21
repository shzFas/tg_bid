import asyncio
import logging
import html

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError

from .config import settings, CATEGORY_TO_CHANNEL
from .db import (
    init_db,
    add_specialist,
    set_specialist_categories,
    get_specialists_list,
    get_specialist_with_categories,
)

logging.basicConfig(level=logging.INFO)
router = Router()


def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list


HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/add_spec tg_id username</code>\n"
    "<code>/set_cats tg_id ACCOUNTING,LAW,EGOV</code>\n"
    "<code>/list_specs</code>\n"
    "<code>/invite_spec tg_id</code> – сгенерировать ссылки для каналов\n"
    "<code>/notify_spec tg_id</code> – отправить ссылки специалисту в ЛС\n\n"
    "<b>📂 Работа с заявками (позже):</b>\n"
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
    await m.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def help_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT, parse_mode="HTML")


# -------------------- /add_spec --------------------


@router.message(Command("add_spec"))
async def add_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return
    if not command.args:
        return await m.answer("<code>Использование: /add_spec tg_id username</code>")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except Exception:
        return await m.answer("<code>tg_id должен быть числом</code>")

    username = parts[1].lstrip("@") if len(parts) == 2 else None

    spec = await add_specialist(tg_id, username)
    safe_spec = html.escape(str(spec))  # защита от HTML-разрушения

    await m.answer(f"<b>OK:</b>\n<code>{safe_spec}</code>", parse_mode="HTML")


# -------------------- /set_cats --------------------


@router.message(Command("set_cats"))
async def set_cats(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>/set_cats tg_id ACCOUNTING,LAW,EGOV</code>")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except Exception:
        return await m.answer("<code>tg_id должен быть числом</code>")

    if len(parts) == 1:
        return await m.answer("<code>Нужно указать категории</code>")

    raw_cats = parts[1].split(",")
    cats = [c.strip().upper() for c in raw_cats]
    allowed = {"ACCOUNTING", "LAW", "EGOV"}

    if any(c not in allowed for c in cats):
        return await m.answer(f"<code>Допустимые категории: {allowed}</code>")

    await set_specialist_categories(tg_id, cats)
    await m.answer("<b>Категории обновлены.</b>", parse_mode="HTML")


# -------------------- /list_specs --------------------


@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()
    if not specs:
        return await m.answer("<code>Пока нет специалистов</code>")

    lines = []
    for s in specs:
        username = html.escape(s.get("username") or "-")
        categories = ", ".join(s["categories"] or [])
        lines.append(
            f"<code>ID={s['id']} TG={s['tg_user_id']} USER=@{username}\n"
            f"CATS: {categories}\n"
            "------------------------</code>"
        )

    await m.answer("\n".join(lines), parse_mode="HTML")


# -------------------- /invite_spec --------------------
# Генерация инвайт-ссылок в каналы по категориям специалиста
# Только для админа


@router.message(Command("invite_spec"))
async def invite_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>Использование: /invite_spec tg_id</code>")

    try:
        tg_id = int(command.args.strip())
    except ValueError:
        return await m.answer("<code>tg_id должен быть числом</code>")

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await m.answer("<code>Специалист не найден. Сначала /add_spec.</code>")

    if not spec["categories"]:
        return await m.answer("<code>У специалиста нет назначенных категорий (/set_cats).</code>")

    links_lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if not chat_id:
            continue

        # Бот-админ должен быть админом в канале!
        invite = await m.bot.create_chat_invite_link(chat_id=chat_id)
        links_lines.append(f"{cat}: {invite.invite_link}")

    if not links_lines:
        return await m.answer("<code>Не удалось создать ссылки, проверь права бота в каналах.</code>")

    msg = (
        f"<b>Ссылки для специалиста tg_id={tg_id}</b>\n"
        f"username=@{html.escape(spec.get('username') or '-')}\n\n"
        + "\n".join(f"<code>{line}</code>" for line in links_lines)
    )
    await m.answer(msg, parse_mode="HTML")


# -------------------- /notify_spec --------------------
# Отправка ссылок специалисту в личку + ссылка на dm-бота


@router.message(Command("notify_spec"))
async def notify_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>Использование: /notify_spec tg_id</code>")

    try:
        tg_id = int(command.args.strip())
    except ValueError:
        return await m.answer("<code>tg_id должен быть числом</code>")

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await m.answer("<code>Специалист не найден.</code>")

    if not spec["categories"]:
        return await m.answer("<code>У специалиста нет категорий. Назначьте через /set_cats.</code>")

    links_lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if not chat_id:
            continue

        invite = await m.bot.create_chat_invite_link(chat_id=chat_id)
        links_lines.append(f"{cat}: {invite.invite_link}")

    if not links_lines:
        return await m.answer("<code>Не удалось создать ссылки для каналов.</code>")

    text_for_spec = (
        "👋 Вас добавили как специалиста.\n\n"
        "Ваши каналы по категориям:\n"
        + "\n".join(links_lines)
        + "\n\n"
        f"Для работы с заявками используйте бота: https://t.me/{settings.DM_BOT_USERNAME}"
    )

    try:
        await m.bot.send_message(tg_id, text_for_spec)
        await m.answer("<code>Уведомление отправлено специалисту.</code>")
    except TelegramForbiddenError:
        await m.answer(
            "<code>Не могу написать специалисту: он ещё не запускал админ-бот. "
            "Попросите его открыть этого бота и нажать /start.</code>"
        )


# -------------------- START BOT --------------------


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
