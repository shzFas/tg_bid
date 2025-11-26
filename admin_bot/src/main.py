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
    "<code>/new_spec</code> – добавить нового специалиста\n"
    "<code>/edit_spec tg_id</code> – изменить данные специалиста\n"
    "<code>/list_specs</code> – список всех специалистов\n"
    "<code>/invite_spec tg_id</code> – ссылки в каналы\n"
    "<code>/notify_spec tg_id</code> – отправить ссылки специалисту\n\n"
)


# -------------------- /start /help --------------------

@router.message(CommandStart())
async def start(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT)


@router.message(Command("help"))
async def help_cmd(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer(HELP_TEXT)


# -------------------- /cancel --------------------

@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    await m.answer("Операция отменена.")


# -------------------- /new_spec --------------------

@router.message(Command("new_spec"))
async def new_spec_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="new")
    await state.set_state(NewSpecForm.WaitingForTgId)

    await m.answer("➕ <b>Добавление нового специалиста</b>\nВведите tg_id:")


# -------------------- /edit_spec --------------------

@router.message(Command("edit_spec"))
async def edit_spec_cmd(m: Message, command: CommandObject, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="edit")

    if command.args:
        try:
            tg_id = int(command.args)
        except:
            return await m.answer("tg_id должен быть числом")

        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer("❌ Специалист не найден")

        await state.update_data(
            tg_id=tg_id,
            full_name=spec["full_name"],
            username=spec["username"],
            categories=spec["categories"] or []
        )
        await state.set_state(NewSpecForm.WaitingForFullName)
        return await m.answer("Введите новое ФИО:")

    await state.set_state(NewSpecForm.WaitingForTgId)
    await m.answer("Введите tg_id специалиста:")


# -------------------- Шаг 1: tg_id --------------------

@router.message(NewSpecForm.WaitingForTgId)
async def spec_got_tg_id(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    try:
        tg_id = int(m.text.strip())
    except:
        return await m.answer("tg_id должен быть числом")

    data = await state.get_data()
    mode = data["mode"]

    if mode == "edit":
        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer("❌ Специалист не найден")

        await state.update_data(
            tg_id=tg_id,
            full_name=spec["full_name"],
            username=spec["username"],
            categories=spec["categories"] or []
        )
        await state.set_state(NewSpecForm.WaitingForFullName)
        return await m.answer("Введите новое ФИО:")

    await state.update_data(tg_id=tg_id)
    await state.set_state(NewSpecForm.WaitingForFullName)
    await m.answer("Введите ФИО специалиста:")


# -------------------- Шаг 2: ФИО --------------------

@router.message(NewSpecForm.WaitingForFullName)
async def spec_got_full_name(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    full_name = m.text.strip()
    if not full_name:
        return await m.answer("ФИО слишком короткое")

    data = await state.get_data()
    tg_id = data["tg_id"]
    username = data.get("username")

    # авто-username
    try:
        chat = await m.bot.get_chat(tg_id)
        if chat.username:
            username = chat.username
    except:
        pass

    await state.update_data(full_name=full_name, username=username)
    await state.set_state(NewSpecForm.ChoosingCategories)

    await m.answer(
        "Выберите категории:",
        reply_markup=categories_kb(selected=data.get("categories", []), mode="new")
    )


# -------------------- new_spec toggle/save --------------------

@router.callback_query(NewSpecForm.ChoosingCategories, F.data.startswith("new_spec:toggle:"))
async def new_spec_toggle(c: CallbackQuery, state: FSMContext):
    _, _, cat = c.data.split(":")

    data = await state.get_data()
    selected = data.get("categories", [])

    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)

    kb = categories_kb(selected=selected, mode="new")
    await c.message.edit_reply_markup(reply_markup=kb)
    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:save")
async def new_spec_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    full_name = data["full_name"]
    username = data["username"]
    categories = data["categories"]

    await add_specialist(tg_user_id=tg_id, username=username, full_name=full_name)
    await set_specialist_categories(tg_id, categories)
    await state.clear()

    await c.message.edit_text(
        f"✅ Добавлен специалист\n\n"
        f"<b>{full_name}</b>\n"
        f"tg_id: {tg_id}\n"
        f"Категории: {', '.join(categories)}"
    )
    await c.answer()


# -------------------- СПИСОК --------------------

@router.message(Command("list_specs"))
async def list_specs(m: Message):
    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, 1)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("spec_list:"))
async def list_specs_page(c: CallbackQuery):
    page = int(c.data.split(":")[1])
    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, page)
    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()


def build_specs_page(specs: list[dict], page: int):
    total = len(specs)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    page = max(1, min(page, pages))
    start = (page-1)*PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = specs[start:end]

    lines = [f"📋 <b>Список специалистов</b> ({page}/{pages})\n"]

    buttons = []

    for s in chunk:
        full_name = html.escape(s["full_name"] or "-")
        cats = ", ".join(s.get("categories") or [])
        buttons.append([
            InlineKeyboardButton(
                text=f"📄 {full_name}",
                callback_data=f"spec_view:{s['tg_user_id']}"
            )
        ])
        lines.append(f"<b>{full_name}</b>\n<code>{cats}</code>\n")

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"spec_list:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"spec_list:{page+1}"))
    if nav:
        buttons.append(nav)

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


# -------------------- КАРТОЧКА --------------------

@router.callback_query(F.data.startswith("spec_view:"))
async def spec_view(c: CallbackQuery):
    tg_id = int(c.data.split(":")[1])
    spec = await get_specialist_with_categories(tg_id)

    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    full_name = html.escape(spec["full_name"] or "-")
    username = html.escape(spec["username"] or "-")
    cats = ", ".join(spec["categories"] or [])

    text = (
        f"📄 <b>Карточка специалиста</b>\n\n"
        f"👤 {full_name}\n"
        f"💬 @{username}\n"
        f"🆔 <code>{tg_id}</code>\n"
        f"📚 {cats or '—'}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Категории", callback_data=f"spec_cat:open:{tg_id}")],
            [InlineKeyboardButton(text="✏️ Редактировать ФИО", callback_data=f"spec_edit:{tg_id}")],
            [
                InlineKeyboardButton(text="🔗 Каналы", callback_data=f"spec_invite:{tg_id}"),
                InlineKeyboardButton(text="📤 ЛС", callback_data=f"spec_notify:{tg_id}")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="spec_back_to_list")]
        ]
    )

    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()


# -------------------- РЕДАКТИРОВАНИЕ ФИО --------------------

@router.callback_query(F.data.startswith("spec_edit:"))
async def spec_edit_cb(c: CallbackQuery, state: FSMContext):
    tg_id = int(c.data.split(":")[1])
    spec = await get_specialist_with_categories(tg_id)

    await state.clear()
    await state.update_data(mode="edit", tg_id=tg_id)

    await state.update_data(
        full_name=spec["full_name"],
        username=spec["username"],
        categories=spec["categories"],
    )

    await state.set_state(NewSpecForm.WaitingForFullName)

    await c.message.edit_text(
        f"✏️ Редактирование ФИО\n\n"
        f"Текущее: <code>{html.escape(spec['full_name'])}</code>\n\n"
        f"Введите новое ФИО:"
    )
    await c.answer()


# -------------------- РЕДАКТИРОВАНИЕ КАТЕГОРИЙ --------------------

@router.callback_query(F.data.startswith("spec_cat:open:"))
async def spec_cat_open(c: CallbackQuery, state: FSMContext):
    tg_id = int(c.data.split(":")[2])

    spec = await get_specialist_with_categories(tg_id)

    await state.clear()
    await state.update_data(tg_id=tg_id, categories=spec["categories"])

    kb = categories_kb(selected=spec["categories"], mode="edit")

    await c.message.edit_text(
        f"📚 Редактирование категорий\n"
        f"<b>{html.escape(spec['full_name'])}</b>",
        reply_markup=kb
    )
    await c.answer()


@router.callback_query(F.data.startswith("spec_cat:toggle:"))
async def spec_cat_toggle(c: CallbackQuery, state: FSMContext):
    cat = c.data.split(":")[2]

    data = await state.get_data()
    selected = data["categories"]

    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)

    kb = categories_kb(selected, mode="edit")
    await c.message.edit_reply_markup(reply_markup=kb)
    await c.answer()


@router.callback_query(F.data == "spec_cat:save")
async def spec_cat_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    categories = data["categories"]

    await set_specialist_categories(tg_id, categories)
    await state.clear()

    await c.message.edit_text(
        f"✅ Категории обновлены:\n<code>{', '.join(categories)}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]]
        )
    )
    await c.answer()


@router.callback_query(F.data == "spec_cat:cancel")
async def spec_cat_cancel(c: CallbackQuery, state: FSMContext):
    tg_id = (await state.get_data()).get("tg_id")
    await state.clear()
    await c.message.edit_text("❌ Отменено", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]]
    ))
    await c.answer()


# -------------------- ССЫЛКИ В ЧАТЫ / ЛИЧКА --------------------

@router.message(Command("invite_spec"))
async def invite_spec_cmd(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("Использование: /invite_spec tg_id")

    tg_id = int(command.args)
    spec = await get_specialist_with_categories(tg_id)

    lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await m.bot.create_chat_invite_link(chat_id)
            lines.append(f"{cat}: {link.invite_link}")

    await m.answer("\n".join(lines) if lines else "❌ Невозможно создать ссылки")


@router.message(Command("notify_spec"))
async def notify_spec_cmd(m: Message, command: CommandObject):
    if not is_admin(m.from_user.id):
        return

    if not command.args:
        return await m.answer("Использование: /notify_spec tg_id")

    tg_id = int(command.args)
    spec = await get_specialist_with_categories(tg_id)

    links = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await m.bot.create_chat_invite_link(chat_id)
            links.append(f"{cat}: {link.invite_link}")

    try:
        await m.bot.send_message(
            tg_id,
            "Ваши категории и каналы:\n" + "\n".join(links)
        )
        await m.answer("Отправлено")
    except TelegramForbiddenError:
        await m.answer("❌ Специалист не открыл бота")


@router.callback_query(F.data.startswith("spec_invite:"))
async def spec_invite_cb(c: CallbackQuery):
    tg_id = int(c.data.split(":")[1])
    spec = await get_specialist_with_categories(tg_id)

    lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await c.bot.create_chat_invite_link(chat_id)
            lines.append(f"{cat}: {link.invite_link}")

    await c.message.edit_text(
        "🔗 Ссылки:\n" + "\n".join(lines) if lines else "❌ Не удалось создать ссылки"
    )
    await c.answer()


@router.callback_query(F.data.startswith("spec_notify:"))
async def spec_notify_cb(c: CallbackQuery):
    tg_id = int(c.data.split(":")[1])
    spec = await get_specialist_with_categories(tg_id)

    links = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            link = await c.bot.create_chat_invite_link(chat_id)
            links.append(f"{cat}: {link.invite_link}")

    try:
        await c.bot.send_message(
            tg_id,
            "Ваши ссылки:\n" + "\n".join(links)
        )
        await c.message.edit_text("Отправлено")
    except TelegramForbiddenError:
        await c.message.edit_text("❌ Специалист не открыл бота")

    await c.answer()


@router.callback_query(F.data == "spec_back_to_list")
async def spec_back_to_list(c: CallbackQuery):
    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, 1)
    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()


# -------------------- START BOT --------------------

async def main():
    await init_db()

    bot = Bot(
        token=settings.ADMIN_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
