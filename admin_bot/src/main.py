import asyncio
import logging
import html

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings, CATEGORY_TO_CHANNEL
from .db import (
    init_db,
    add_specialist,
    set_specialist_categories,
    get_specialists_list,
    get_specialist_with_categories,
)
from .states import NewSpecForm
from .keyboards import categories_kb

logging.basicConfig(level=logging.INFO)
router = Router()


def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list


HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/new_spec</code> – мастер добавления специалиста\n"
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


# -------------------- /start /help --------------------


@router.message(CommandStart())
async def start(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def help_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT, parse_mode="HTML")


# -------------------- Мастер /new_spec --------------------
# Шаг 1: спросить tg_id
# Шаг 2: выбрать категории по кнопкам
# Шаг 3: сохранить или отменить

@router.message(Command("new_spec"))
async def new_spec_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.set_state(NewSpecForm.WaitingForTgId)
    await m.answer(
        "Введите <code>tg_id</code> специалиста (число).\n\n"
        "Например: <code>6296976773</code>\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("Операция отменена.", parse_mode="HTML")


@router.message(NewSpecForm.WaitingForTgId)
async def new_spec_got_tg_id(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    try:
        tg_id = int((m.text or "").strip())
    except:
        return await m.answer("❌ tg_id должен быть числом.")

    await state.update_data(tg_id=tg_id)
    await state.set_state(NewSpecForm.WaitingForFullName)
    await m.answer("Введите ФИО специалиста (например: <code>Иван Иванов</code>)", parse_mode="HTML")

@router.message(NewSpecForm.WaitingForFullName)
async def new_spec_got_name(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    full_name = (m.text or "").strip()
    if len(full_name) < 3:
        return await m.answer("❌ ФИО слишком короткое. Попробуйте ещё или /cancel")

    data = await state.get_data()
    tg_id = data["tg_id"]

    # 🔍 Попробуем получить username по Telegram API
    try:
        chat = await m.bot.get_chat(tg_id)
        username = chat.username  # может быть None
    except:
        username = None  # если не получилось

    await state.update_data(full_name=full_name, username=username, categories=[])
    await state.set_state(NewSpecForm.ChoosingCategories)

    await m.answer(
        f"📌 Данные специалиста:\n"
        f"ID: <code>{tg_id}</code>\n"
        f"ФИО: <code>{full_name}</code>\n"
        f"username: <code>{username or '- (нет)'}</code>\n\n"
        "Теперь выберите категории:",
        reply_markup=categories_kb(selected=[]),
        parse_mode="HTML"
    )


@router.callback_query(NewSpecForm.ChoosingCategories, F.data.startswith("new_spec:cat:"))
async def new_spec_toggle_category(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    selected: list[str] = data.get("categories", []) or []

    _, _, cat = c.data.split(":", 2)  # new_spec:cat:LAW
    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)

    try:
        await c.message.edit_reply_markup(reply_markup=categories_kb(selected=selected))
    except Exception:
        pass

    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:cancel")
async def new_spec_cancel_cb(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await c.message.edit_text("Операция добавления специалиста отменена.")
    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:save")
async def new_spec_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    full_name = data["full_name"]
    username = data["username"]
    categories = data["categories"] or []

    spec = await add_specialist(
        tg_user_id=tg_id,
        username=username,
        full_name=full_name
    )
    await set_specialist_categories(tg_id, categories)

    await state.clear()

    await c.message.edit_text(
        f"<b>Специалист сохранён</b>\n"
        f"ID: <code>{tg_id}</code>\n"
        f"ФИО: <code>{full_name}</code>\n"
        f"Username: <code>{username or '- (нет)'}</code>\n"
        f"Категории: <code>{','.join(categories)}</code>",
        parse_mode="HTML"
    )
    await c.answer("Сохранено! ✅")


# -------------------- /add_spec (остаётся для ручного ввода) --------------------


@router.message(Command("add_spec"))
async def add_spec_cmd(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return
    if not command.args:
        return await m.answer("<code>Использование: /add_spec tg_id username</code>", parse_mode="HTML")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except Exception:
        return await m.answer("<code>tg_id должен быть числом</code>", parse_mode="HTML")

    username = parts[1].lstrip("@") if len(parts) == 2 else None

    spec = await add_specialist(tg_id, username)
    safe_spec = html.escape(str(spec))

    await m.answer(f"<b>OK:</b>\n<code>{safe_spec}</code>", parse_mode="HTML")


# -------------------- /set_cats --------------------


@router.message(Command("set_cats"))
async def set_cats(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>/set_cats tg_id ACCOUNTING,LAW,EGOV</code>", parse_mode="HTML")

    parts = command.args.split(maxsplit=1)
    try:
        tg_id = int(parts[0])
    except Exception:
        return await m.answer("<code>tg_id должен быть числом</code>", parse_mode="HTML")

    if len(parts) == 1:
        return await m.answer("<code>Нужно указать категории</code>", parse_mode="HTML")

    raw_cats = parts[1].split(",")
    cats = [c.strip().upper() for c in raw_cats]
    allowed = {"ACCOUNTING", "LAW", "EGOV"}

    if any(c not in allowed for c in cats):
        return await m.answer(f"<code>Допустимые категории: {allowed}</code>", parse_mode="HTML")

    await set_specialist_categories(tg_id, cats)
    await m.answer("<b>Категории обновлены.</b>", parse_mode="HTML")


# -------------------- /list_specs --------------------


@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()
    if not specs:
        return await m.answer("<code>Пока нет специалистов</code>", parse_mode="HTML")

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


@router.message(Command("invite_spec"))
async def invite_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>Использование: /invite_spec tg_id</code>", parse_mode="HTML")

    try:
        tg_id = int(command.args.strip())
    except ValueError:
        return await m.answer("<code>tg_id должен быть числом</code>", parse_mode="HTML")

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await m.answer("<code>Специалист не найден. Сначала /add_spec или /new_spec.</code>", parse_mode="HTML")

    if not spec["categories"]:
        return await m.answer("<code>У специалиста нет назначенных категорий (/set_cats).</code>", parse_mode="HTML")

    links_lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if not chat_id:
            continue
        invite = await m.bot.create_chat_invite_link(chat_id=chat_id)
        links_lines.append(f"{cat}: {invite.invite_link}")

    if not links_lines:
        return await m.answer("<code>Не удалось создать ссылки, проверь права бота в каналах.</code>", parse_mode="HTML")

    msg = (
        f"<b>Ссылки для специалиста tg_id={tg_id}</b>\n"
        f"username=@{html.escape(spec.get('username') or '-')}\n\n"
        + "\n".join(f"<code>{line}</code>" for line in links_lines)
    )
    await m.answer(msg, parse_mode="HTML")


# -------------------- /notify_spec --------------------


@router.message(Command("notify_spec"))
async def notify_spec(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("<code>Использование: /notify_spec tg_id</code>", parse_mode="HTML")

    try:
        tg_id = int(command.args.strip())
    except ValueError:
        return await m.answer("<code>tg_id должен быть числом</code>", parse_mode="HTML")

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await m.answer("<code>Специалист не найден.</code>", parse_mode="HTML")

    if not spec["categories"]:
        return await m.answer("<code>У специалиста нет категорий. Назначьте через /set_cats или /new_spec.</code>", parse_mode="HTML")

    links_lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if not chat_id:
            continue
        invite = await m.bot.create_chat_invite_link(chat_id=chat_id)
        links_lines.append(f"{cat}: {invite.invite_link}")

    if not links_lines:
        return await m.answer("<code>Не удалось создать ссылки для каналов.</code>", parse_mode="HTML")

    text_for_spec = (
        "👋 Вас добавили как специалиста.\n\n"
        "Ваши каналы по категориям:\n"
        + "\n".join(links_lines)
        + "\n\n"
        f"Для работы с заявками используйте бота: https://t.me/{settings.DM_BOT_USERNAME}"
    )

    try:
        await m.bot.send_message(tg_id, text_for_spec)
        await m.answer("<code>Уведомление отправлено специалисту.</code>", parse_mode="HTML")
    except TelegramForbiddenError:
        await m.answer(
            "<code>Не могу написать специалисту: он ещё не запускал этого бота. "
            "Попросите его открыть бота и нажать /start.</code>",
            parse_mode="HTML",
        )


# -------------------- START BOT --------------------


async def main():
    await init_db()

    bot = Bot(
        token=settings.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
