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


# -------------------- /new_spec (Шаги) --------------------

@router.message(Command("new_spec"))
async def new_spec_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="new")
    await state.set_state(NewSpecForm.WaitingForTgId)

    await m.answer(
        "➕ <b>Добавление нового специалиста</b>\n\n"
        "Введите <code>tg_id</code> специалиста:",
        parse_mode="HTML",
    )


# -------------------- /edit_spec --------------------

@router.message(Command("edit_spec"))
async def edit_spec_cmd(m: Message, command: CommandObject, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="edit")

    if command.args:
        try:
            tg_id = int(command.args.strip())
        except ValueError:
            return await m.answer("❌ tg_id должен быть числом", parse_mode="HTML")

        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer("❌ Специалист не найден.", parse_mode="HTML")

        await state.update_data(
            tg_id=tg_id,
            full_name=spec.get("full_name"),
            username=spec.get("username"),
            categories=spec.get("categories") or [],
        )

        await state.set_state(NewSpecForm.WaitingForFullName)
        await m.answer("Введите новое ФИО:", parse_mode="HTML")
        return

    await state.set_state(NewSpecForm.WaitingForTgId)
    await m.answer("Введите tg_id специалиста:", parse_mode="HTML")


# -------------------- Шаг 1: tg_id --------------------

@router.message(NewSpecForm.WaitingForTgId)
async def spec_got_tg_id(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    try:
        tg_id = int(m.text.strip())
    except:
        return await m.answer("❌ tg_id должен быть числом")

    data = await state.get_data()
    mode = data.get("mode", "new")

    # Если редактируем — подгрузить данные
    if mode == "edit":
        spec = await get_specialist_with_categories(tg_id)
        if not spec:
            return await m.answer("❌ Специалист не найден.", parse_mode="HTML")

        await state.update_data(
            tg_id=tg_id,
            full_name=spec.get("full_name"),
            username=spec.get("username"),
            categories=spec.get("categories") or [],
        )
        await state.set_state(NewSpecForm.WaitingForFullName)
        return await m.answer("Введите ФИО специалиста:", parse_mode="HTML")

    # Новый специалист
    await state.update_data(tg_id=tg_id)
    await state.set_state(NewSpecForm.WaitingForFullName)
    await m.answer("Введите ФИО специалиста:", parse_mode="HTML")


# -------------------- Шаг 2: ФИО --------------------

@router.message(NewSpecForm.WaitingForFullName)
async def spec_got_full_name(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    full_name = m.text.strip()
    if not full_name:
        return await m.answer("❌ ФИО слишком короткое")

    data = await state.get_data()
    tg_id = data["tg_id"]
    username = data.get("username")

    # автоматическое получение username из Telegram
    try:
        chat = await m.bot.get_chat(tg_id)
        if chat.username:
            username = chat.username
    except:
        pass

    await state.update_data(full_name=full_name, username=username)
    await state.set_state(NewSpecForm.ChoosingCategories)

    await m.answer(
        "Выберите категории специалиста:",
        reply_markup=categories_kb(selected=data.get("categories", [])),
    )


# -------------------- Выбор категорий --------------------

@router.callback_query(NewSpecForm.ChoosingCategories, F.data.startswith("new_spec:cat:"))
async def toggle_category(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа", show_alert=True)

    data = await state.get_data()
    selected = data.get("categories", []) or []

    _, _, cat = c.data.split(":", 2)

    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)

    await c.message.edit_reply_markup(categories_kb(selected))
    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:save")
async def new_spec_save(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа", show_alert=True)

    data = await state.get_data()

    tg_id = data["tg_id"]
    full_name = data["full_name"]
    username = data.get("username")
    categories = data.get("categories", [])

    await add_specialist(tg_user_id=tg_id, username=username, full_name=full_name)
    await set_specialist_categories(tg_id, categories)

    await state.clear()

    cats_str = ", ".join(categories)
    await c.message.edit_text(
        f"✅ Данные сохранены.\n\n"
        f"<b>{full_name}</b>\n"
        f"tg_id: <code>{tg_id}</code>\n"
        f"username: @{username}\n"
        f"Категории: <code>{cats_str}</code>\n",
        parse_mode="HTML",
    )
    await c.answer()


# -------------------- СПИСОК СПЕЦИАЛИСТОВ --------------------

@router.message(Command("list_specs"))
async def list_specs(m: Message):
    if not is_admin(m.from_user.id):
        return

    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, page=1)

    await m.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("spec_list:"))
async def specs_pagination(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    _, page_str = c.data.split(":", 1)
    page = int(page_str)

    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, page)

    try:
        await c.message.edit_text(text, reply_markup=kb)
    except:
        await c.message.answer(text, reply_markup=kb)

    await c.answer()


# ---------------- USER-FRIENDLY VIEW -----------------

def build_specs_page(specs: list[dict], page: int):

    total = len(specs)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, pages))

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = specs[start:end]

    lines = [f"📋 <b>Список специалистов</b> (стр. {page}/{pages}, всего {total})\n"]

    for idx, s in enumerate(chunk, start=start + 1):
        full_name = html.escape(s.get("full_name") or "-")
        username = html.escape(s.get("username") or "-")
        cats = ", ".join(s.get("categories") or [])

        lines.append(
            f"<b>{idx}.</b> {full_name}\n"
            f"🔹 <code>{cats or '—'}</code>"
        )

    text = "\n".join(lines)

    buttons = []

    # кнопки "Открыть"
    for s in chunk:
        buttons.append([
            InlineKeyboardButton(
                text=f"📄 {html.escape(s.get('full_name') or '-')}",
                callback_data=f"spec_view:{s['tg_user_id']}"
            )
        ])

    # Навигация
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"spec_list:{page - 1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"spec_list:{page + 1}"))
    if nav:
        buttons.append(nav)

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


# -------------------- КАРТОЧКА СПЕЦИАЛИСТА --------------------

@router.callback_query(F.data.startswith("spec_view:"))
async def view_spec_card(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа", show_alert=True)

    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    full_name = html.escape(spec.get("full_name") or "-")
    username = html.escape(spec.get("username") or "-")
    cats = ", ".join(spec.get("categories") or [])

    text = (
        "📄 <b>Карточка специалиста</b>\n\n"
        f"👤 <b>ФИО:</b> {full_name}\n"
        f"💬 <b>username:</b> @{username}\n"
        f"🆔 <b>tg_id:</b> <code>{tg_id}</code>\n"
        f"📚 <b>Категории:</b> <code>{cats or '—'}</code>\n"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Категории", callback_data=f"spec_cat:open:{tg_id}")],
            [InlineKeyboardButton(text="✏️ Редактировать ФИО", callback_data=f"spec_edit:{tg_id}")],
            [
                InlineKeyboardButton(text="🔗 Каналы", callback_data=f"spec_invite:{tg_id}"),
                InlineKeyboardButton(text="📤 Отправить ссылки", callback_data=f"spec_notify:{tg_id}")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="spec_back_to_list")]
        ]
    )

    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()
    

@router.callback_query(F.data.startswith("spec_edit:"))
async def spec_edit_cb(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    # имитируем команду /edit_spec tg_id
    await state.clear()
    await state.update_data(mode="edit", tg_id=tg_id)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    await state.update_data(
        full_name=spec.get("full_name"),
        username=spec.get("username"),
        categories=spec.get("categories") or [],
    )

    await state.set_state(NewSpecForm.WaitingForFullName)

    await c.message.edit_text(
        f"✏️ <b>Редактирование специалиста</b>\n\n"
        f"Текущее ФИО: <code>{html.escape(spec.get('full_name') or '-')}</code>\n\n"
        "Введите новое ФИО:",
        parse_mode="HTML"
    )
    await c.answer()
    
@router.callback_query(F.data.startswith("spec_categories:"))
async def spec_categories_cb(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    # сохраняем в FSM
    await state.clear()
    await state.update_data(tg_id=tg_id, categories=spec.get("categories") or [])

    text = (
        f"📚 <b>Категории специалиста</b>\n\n"
        f"ФИО: <code>{html.escape(spec.get('full_name') or '-')}</code>\n"
        f"Выберите категории:"
    )

    from .keyboards import categories_kb  # на всякий случай

    kb = categories_kb(selected=spec.get("categories") or [], save_callback="spec_categories_save")

    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()
    
@router.callback_query(F.data.startswith("spec_cat:open:"))
async def spec_cat_open(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа", show_alert=True)

    _, _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    await state.clear()
    await state.update_data(tg_id=tg_id, categories=spec.get("categories") or [])

    text = (
        "📚 <b>Изменение категорий специалиста</b>\n\n"
        f"👤 <b>{html.escape(spec.get('full_name') or '-')}</b>\n"
        "Выберите категории:"
    )

    kb = categories_kb(selected=spec.get("categories") or [], mode="edit")

    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()

@router.callback_query(F.data.startswith("spec_cat:toggle:"))
async def spec_cat_toggle(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    parts = c.data.split(":")
    code = parts[2]  # LAW / ACCOUNTING / EGOV

    data = await state.get_data()
    selected = data.get("categories", [])

    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)

    await state.update_data(categories=selected)

    from .keyboards import categories_kb
    kb = categories_kb(selected=selected, mode="edit")

    await c.message.edit_reply_markup(reply_markup=kb)  # <-- ВАЖНО!
    await c.answer()


@router.callback_query(F.data.startswith("spec_categories:cat:"))
async def spec_categories_toggle(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    data = await state.get_data()
    selected = data.get("categories", [])

    _, _, cat = c.data.split(":", 2)

    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)

    from .keyboards import categories_kb

    await c.message.edit_reply_markup(categories_kb(selected, save_callback="spec_categories_save"))
    await c.answer()

@router.callback_query(F.data == "spec_categories_save")
async def spec_categories_save(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    data = await state.get_data()
    tg_id = data["tg_id"]
    categories = data.get("categories", [])

    await set_specialist_categories(tg_id, categories)

    cats_str = ", ".join(categories) if categories else "—"

    await state.clear()

    await c.message.edit_text(
        f"✅ Категории обновлены.\n\n"
        f"Новые категории: <code>{cats_str}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]
            ]
        )
    )
    await c.answer()
    
@router.callback_query(F.data == "spec_cat:save")
async def spec_cat_save(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    data = await state.get_data()
    tg_id = data["tg_id"]
    categories = data.get("categories", [])

    await set_specialist_categories(tg_id, categories)

    await state.clear()

    cats_str = ", ".join(categories) if categories else "—"

    await c.message.edit_text(
        f"✅ Категории обновлены.\n\nНовые категории: <code>{cats_str}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]
            ]
        )
    )

    await c.answer()
    
@router.callback_query(F.data == "spec_cat:cancel")
async def spec_cat_cancel(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data.get("tg_id")

    await state.clear()

    await c.message.edit_text("❌ Отменено", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]]
    ))
    await c.answer()


@router.callback_query(F.data.startswith("spec_invite:"))
async def spec_invite_cb(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    # просто вызвать существующую логику
    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    lines = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if not chat_id:
            continue
        invite = await c.bot.create_chat_invite_link(chat_id)
        lines.append(f"{cat}: {invite.invite_link}")

    text = (
        f"🔗 <b>Ссылки для специалиста</b>\n\n" + "\n".join(lines)
        if lines else "❌ Не удалось создать ссылки."
    )

    await c.message.edit_text(text)
    await c.answer()

@router.callback_query(F.data.startswith("spec_notify:"))
async def spec_notify_cb(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа")

    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    links = []
    for cat in spec["categories"]:
        chat_id = CATEGORY_TO_CHANNEL.get(cat)
        if chat_id:
            invite = await c.bot.create_chat_invite_link(chat_id)
            links.append(f"{cat}: {invite.invite_link}")

    try:
        await c.bot.send_message(
            tg_id,
            "👋 Вас добавили как специалиста:\n\n" + "\n".join(links)
        )
        await c.message.edit_text("✅ Отправлено в ЛС специалисту")
    except TelegramForbiddenError:
        await c.message.edit_text("❌ Специалист не открыл бота")


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
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
