import asyncio
import logging
import html
import math

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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

PAGE_SIZE = 5 


def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list


HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/new_spec</code> – добавить нового специалиста (мастер)\n"
    "<code>/edit_spec tg_id</code> – изменить данные специалиста\n"
    "<code>/list_specs</code> – список всех специалистов\n"
    "<code>/invite_spec tg_id</code> – ссылки в каналы по категориям\n"
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


# -------------------- /cancel --------------------


@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("Операция отменена.", parse_mode="HTML")


# -------------------- Мастер /new_spec --------------------
# mode = "new"
# Шаг 1: tg_id → Шаг 2: ФИО → Шаг 3: категории → Сохранить


@router.message(Command("new_spec"))
async def new_spec_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="new")  # создаём нового
    await state.set_state(NewSpecForm.WaitingForTgId)

    await m.answer(
        "➕ <b>Добавление нового специалиста</b>\n\n"
        "Введите <code>tg_id</code> специалиста (число).\n\n"
        "Например: <code>6296976773</code>\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
    )


# -------------------- /edit_spec --------------------
# mode = "edit"
# Можно так: /edit_spec   → спросит tg_id
# или так:  /edit_spec 6296976773 → сразу грузит данные


@router.message(Command("edit_spec"))
async def edit_spec_cmd(m: Message, command: CommandObject, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="edit")

    # если tg_id передан сразу: /edit_spec 6296976773
    if command.args:
        try:
            tg_id = int(command.args.strip())
        except ValueError:
            return await m.answer(
                "❌ <b>tg_id должен быть числом.</b>\nПопробуйте ещё раз или /cancel",
                parse_mode="HTML",
            )

        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer(
                "<code>Специалист с таким tg_id не найден. Сначала добавьте его через /new_spec.</code>",
                parse_mode="HTML",
            )

        await state.update_data(
            tg_id=tg_id,
            full_name=spec.get("full_name") or "",
            username=spec.get("username"),
            categories=spec.get("categories") or [],
        )
        await state.set_state(NewSpecForm.WaitingForFullName)

        cats_str = ", ".join(spec.get("categories") or [])
        await m.answer(
            "✏️ <b>Редактирование специалиста</b>\n\n"
            f"Текущие данные:\n"
            f"tg_id: <code>{tg_id}</code>\n"
            f"ФИО: <code>{html.escape(spec.get('full_name') or '- (нет)')}</code>\n"
            f"Username: <code>{html.escape(spec.get('username') or '- (нет)')}</code>\n"
            f"Категории: <code>{cats_str or '- (нет)'}</code>\n\n"
            "Отправьте <b>новое ФИО</b> (или то же самое, если не хотите менять).\n\n"
            "Для отмены — /cancel",
            parse_mode="HTML",
        )
        return

    # если аргумент не передан — спросим tg_id
    await state.set_state(NewSpecForm.WaitingForTgId)
    await m.answer(
        "✏️ <b>Редактирование специалиста</b>\n\n"
        "Введите <code>tg_id</code> специалиста (число).\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
    )


# -------------------- Общий шаг: ввод tg_id --------------------


@router.message(NewSpecForm.WaitingForTgId)
async def spec_got_tg_id(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    text = (m.text or "").strip()
    try:
        tg_id = int(text)
    except Exception:
        return await m.answer(
            "❌ <code>tg_id</code> должен быть числом. Попробуйте ещё раз или /cancel",
            parse_mode="HTML",
        )

    data = await state.get_data()
    mode = data.get("mode", "new")

    if mode == "edit":
        # ищем существующего специалиста
        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer(
                "<code>Специалист с таким tg_id не найден. Сначала добавьте его через /new_spec.</code>",
                parse_mode="HTML",
            )

        await state.update_data(
            tg_id=tg_id,
            full_name=spec.get("full_name") or "",
            username=spec.get("username"),
            categories=spec.get("categories") or [],
        )
        await state.set_state(NewSpecForm.WaitingForFullName)

        cats_str = ", ".join(spec.get("categories") or [])
        await m.answer(
            "✏️ <b>Редактирование специалиста</b>\n\n"
            f"Текущие данные:\n"
            f"tg_id: <code>{tg_id}</code>\n"
            f"ФИО: <code>{html.escape(spec.get('full_name') or '- (нет)')}</code>\n"
            f"Username: <code>{html.escape(spec.get('username') or '- (нет)')}</code>\n"
            f"Категории: <code>{cats_str or '- (нет)'}</code>\n\n"
            "Отправьте <b>новое ФИО</b> (или то же самое, если не хотите менять).\n\n"
            "Для отмены — /cancel",
            parse_mode="HTML",
        )
        return

    # mode == "new"
    await state.update_data(tg_id=tg_id)
    await state.set_state(NewSpecForm.WaitingForFullName)
    await m.answer(
        f"🆔 tg_id = <code>{tg_id}</code>\n\n"
        "Теперь введите <b>ФИО специалиста</b>, например:\n"
        "<code>Иван Иванов</code>\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
    )


# -------------------- Общий шаг: ввод ФИО --------------------


@router.message(NewSpecForm.WaitingForFullName)
async def spec_got_full_name(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    full_name = (m.text or "").strip()
    if len(full_name) < 3:
        return await m.answer(
            "❌ ФИО слишком короткое. Попробуйте ещё раз или /cancel",
            parse_mode="HTML",
        )

    data = await state.get_data()
    tg_id = data.get("tg_id")
    if tg_id is None:
        await state.clear()
        return await m.answer("tg_id потерян. Начните заново: /new_spec", parse_mode="HTML")

    mode = data.get("mode", "new")
    username = data.get("username")

    # пробуем обновить username по Telegram API
    try:
        chat = await m.bot.get_chat(tg_id)
        if chat.username:
            username = chat.username
    except Exception:
        pass

    await state.update_data(full_name=full_name, username=username)

    current_categories: list[str] = data.get("categories", []) or []

    await state.set_state(NewSpecForm.ChoosingCategories)
    await m.answer(
        (
            "📌 Данные специалиста:\n"
            f"tg_id: <code>{tg_id}</code>\n"
            f"ФИО: <code>{html.escape(full_name)}</code>\n"
            f"Username: <code>{html.escape(username or '- (нет)')}</code>\n\n"
            "Теперь выберите категории специалиста:"
        ),
        reply_markup=categories_kb(selected=current_categories),
        parse_mode="HTML",
    )


# -------------------- Выбор категорий (callback) --------------------


@router.callback_query(NewSpecForm.ChoosingCategories, F.data.startswith("new_spec:cat:"))
async def toggle_category(c: CallbackQuery, state: FSMContext):
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
    await c.message.edit_text("Операция добавления/редактирования специалиста отменена.")
    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:save")
async def new_spec_save(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    tg_id = data.get("tg_id")
    full_name = data.get("full_name")
    username = data.get("username")
    categories: list[str] = data.get("categories", []) or []
    mode = data.get("mode", "new")

    if tg_id is None:
        await c.answer("tg_id потерян, начните заново: /new_spec", show_alert=True)
        return
    if not full_name:
        await c.answer("ФИО не задано, начните заново: /new_spec", show_alert=True)
        return
    if not categories:
        await c.answer("Выберите хотя бы одну категорию.", show_alert=True)
        return

    # создаём / обновляем специалиста в БД
    spec = await add_specialist(
        tg_user_id=tg_id,
        username=username,
        full_name=full_name,
    )
    await set_specialist_categories(tg_id, categories)

    await state.clear()

    cats_str = ", ".join(categories)
    safe_spec = html.escape(str(spec))
    prefix = "Добавлен новый специалист." if mode == "new" else "Данные специалиста обновлены."

    text = (
        f"<b>{prefix}</b>\n\n"
        f"<code>{safe_spec}</code>\n\n"
        f"ФИО: <code>{html.escape(full_name)}</code>\n"
        f"Username: <code>{html.escape(username or '- (нет)')}</code>\n"
        f"Категории: <code>{cats_str}</code>\n\n"
        "Теперь вы можете использовать:\n"
        f"<code>/invite_spec {tg_id}</code> – ссылки в каналы\n"
        f"<code>/notify_spec {tg_id}</code> – отправить всё ему в ЛС"
    )

    await c.message.edit_text(text, parse_mode="HTML")
    await c.answer("Сохранено ✅")


# -------------------- /list_specs --------------------


@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()  # пусть вернёт всех, мы режем по 5
    if not specs:
        return await m.answer("Пока нет зарегистрированных специалистов.", parse_mode="HTML")

    text, kb = build_specs_page(specs, page=1)
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("spec_list:"))
async def specs_pagination(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        await c.answer("Нет доступа", show_alert=True)
        return

    try:
        _, page_str = c.data.split(":", 1)
        page = int(page_str)
    except Exception:
        await c.answer()
        return

    specs = await get_specialists_list()
    if not specs:
        await c.message.edit_text("Пока нет зарегистрированных специалистов.", parse_mode="HTML")
        await c.answer()
        return

    text, kb = build_specs_page(specs, page=page)
    try:
        await c.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # на всякий случай, если Telegram не даёт редактировать
        await c.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await c.answer()



def build_specs_page(specs: list[dict], page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Возвращает (text, keyboard) для списка специалистов на указанной странице.
    """
    total = len(specs)
    if total == 0:
        return "Пока нет зарегистрированных специалистов.", None

    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = specs[start:end]

    lines: list[str] = []
    lines.append(f"👨‍⚖️ <b>Список специалистов</b> (стр. {page}/{pages}, всего {total})\n")

    for idx, s in enumerate(chunk, start=start + 1):
        full_name = html.escape(s.get("full_name") or "-")
        username = html.escape(s.get("username") or "-")
        cats = ", ".join(s.get("categories") or [])
        lines.append(
            f"<b>{idx}.</b> {full_name}\n"
            f"🔹 ФИО: <code>{full_name}</code>\n"
            f"🔹 tg_id: <code>{s['tg_user_id']}</code>\n"
            f"🔹 username: <code>@{username}</code>\n"
            f"🔹 категории: <code>{cats or '—'}</code>\n"
            "-------------------------"
        )

    text = "\n".join(lines)

    # Клавиатура пагинации
    buttons: list[list[InlineKeyboardButton]] = []
    nav_row: list[InlineKeyboardButton] = []

    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"spec_list:{page-1}",
            )
        )
    if page < pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"spec_list:{page+1}",
            )
        )

    if nav_row:
        buttons.append(nav_row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    return text, kb


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
        return await m.answer("<code>Специалист не найден. Сначала /new_spec.</code>", parse_mode="HTML")

    if not spec["categories"]:
        return await m.answer("<code>У специалиста нет категорий (/edit_spec или /new_spec).</code>", parse_mode="HTML")

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
        f"ФИО: <code>{html.escape(spec.get('full_name') or '-')}</code>\n"
        f"username=@{html.escape(spec.get('username') or '-')}</f>\n\n"
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
        return await m.answer("<code>У специалиста нет категорий. Используйте /edit_spec или /new_spec.</code>", parse_mode="HTML")

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
