import asyncio
import logging
import hmac
import hashlib

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from .config import settings, CATEGORY_TO_CHANNEL
from .states import RequestForm
from .keyboards import (
    nav_kb, categories_kb, phone_kb,
    confirm_kb, claim_kb, open_dm_external_kb
)
from .texts import *
from .utils import preview_text, now_local_str
from .db import init_db, save_request, get_request_by_message_id, set_status_in_progress

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

router = Router()

# мини-кэш в памяти (msg_id -> {user_id, username})
active_requests: dict[int, dict] = {}


# ----------------------------------------------------
# SHORT TOKEN GENERATOR FOR DM_BOT
# ----------------------------------------------------

def make_short_token(message_id: int) -> str:
    """
    Создаёт короткий токен вида:
    <hex_msg_id>.<first16-HMAC>
    """
    if not settings.SHARED_SECRET:
        raise RuntimeError("SHARED_SECRET is not set in .env for bot #1")

    mid_hex = format(message_id, "x")
    sig = hmac.new(
        settings.SHARED_SECRET.encode(),
        mid_hex.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{mid_hex}.{sig}"


# ----------------------------------------------------
# START
# ----------------------------------------------------

@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RequestForm.Phone)

    await m.answer(HELLO, reply_markup=phone_kb())
    await m.answer(ASK_PHONE, reply_markup=nav_kb())


# ----------------------------------------------------
# PHONE
# ----------------------------------------------------

@router.message(RequestForm.Phone, F.contact)
async def got_contact(m: Message, state: FSMContext):
    phone = m.contact.phone_number if m.contact else None
    if not phone:
        await m.answer("Не получил номер, введите вручную:", reply_markup=nav_kb())
        return

    await state.update_data(phone=phone)
    await ask_name(m, state)


@router.message(RequestForm.Phone, F.text)
async def phone_text(m: Message, state: FSMContext):
    txt = m.text.strip()
    if len(txt) < 6:
        await m.answer("Похоже, это не номер. Введите снова.", reply_markup=nav_kb())
        return

    await state.update_data(phone=txt)
    await ask_name(m, state)


async def ask_name(m: Message, state: FSMContext):
    await state.set_state(RequestForm.Name)
    await m.answer(ASK_NAME, reply_markup=nav_kb())


# ----------------------------------------------------
# NAME
# ----------------------------------------------------

@router.message(RequestForm.Name, F.text)
async def got_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(RequestForm.Category)

    await m.answer(ASK_CATEGORY, reply_markup=categories_kb())
    await m.answer("Выберите категорию кнопкой ниже ⤵️", reply_markup=ReplyKeyboardRemove())


# ----------------------------------------------------
# CATEGORY
# ----------------------------------------------------

@router.callback_query(RequestForm.Category, F.data.startswith("cat:"))
async def choose_category(c: CallbackQuery, state: FSMContext):
    _, cat = c.data.split(":", 1)

    await state.update_data(category=cat)
    await state.set_state(RequestForm.City)

    await c.message.edit_text(ASK_CITY, reply_markup=nav_kb())
    await c.answer()


@router.message(RequestForm.Category)
async def must_click_category(m: Message):
    await m.answer("Выберите категорию кнопкой ниже 👇", reply_markup=categories_kb())


# ----------------------------------------------------
# CITY
# ----------------------------------------------------

@router.message(RequestForm.City, F.text)
async def got_city(m: Message, state: FSMContext):
    await state.update_data(city=m.text.strip())
    await state.set_state(RequestForm.Description)

    await m.answer(ASK_DESC, reply_markup=nav_kb())


# ----------------------------------------------------
# DESCRIPTION
# ----------------------------------------------------

@router.message(RequestForm.Description, F.text)
async def got_desc(m: Message, state: FSMContext):
    await state.update_data(description=m.text.strip())

    data = await state.get_data()
    await state.set_state(RequestForm.Confirm)

    preview = preview_text(data)
    await m.answer(CONFIRM.format(preview=preview), reply_markup=confirm_kb())


# ----------------------------------------------------
# NAVIGATION (BACK / STOP / CANCEL)
# ----------------------------------------------------

@router.callback_query(F.data == "nav:stop")
async def nav_stop(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(STOPPED)
    await c.answer()


@router.callback_query(F.data == "nav:cancel")
async def nav_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(CANCELED)
    await c.answer()


@router.callback_query(F.data == "nav:back")
async def nav_back(c: CallbackQuery, state: FSMContext):
    st = await state.get_state()

    if st == RequestForm.Name.state:
        await state.set_state(RequestForm.Phone)
        await c.message.edit_text(ASK_PHONE)
    elif st == RequestForm.Category.state:
        await state.set_state(RequestForm.Name)
        await c.message.edit_text(ASK_NAME)
    elif st == RequestForm.City.state:
        await state.set_state(RequestForm.Category)
        await c.message.edit_text(ASK_CATEGORY, reply_markup=categories_kb())
    elif st == RequestForm.Description.state:
        await state.set_state(RequestForm.City)
        await c.message.edit_text(ASK_CITY)
    elif st == RequestForm.Confirm.state:
        await state.set_state(RequestForm.Description)
        await c.message.edit_text(ASK_DESC)
    else:
        await c.message.answer("Назад сейчас недоступно.")

    await c.answer()


# ----------------------------------------------------
# CONFIRM SEND
# ----------------------------------------------------

@router.callback_query(RequestForm.Confirm, F.data == "confirm:edit")
async def confirm_edit(c: CallbackQuery, state: FSMContext):
    await state.set_state(RequestForm.Description)
    await c.message.edit_text(ASK_DESC, reply_markup=nav_kb())
    await c.answer()


@router.callback_query(RequestForm.Confirm, F.data == "confirm:send")
async def confirm_send(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    required = ["phone", "name", "category", "city", "description"]

    if not all(data.get(k) for k in required):
        await c.answer("Не хватает данных", show_alert=True)
        return

    category = data["category"]
    channel_id = CATEGORY_TO_CHANNEL.get(category)

    if not channel_id:
        await c.answer("Канал для категории не настроен!", show_alert=True)
        return

    created_at = now_local_str()

    # текст в канал
    text_channel = PUBLISHED_TEMPLATE.format(
        name=data["name"],
        category_h=CATEGORY_H[category],
        city=data["city"],
        description=data["description"],
        created_at=created_at,
    )

    # текст админу (копия)
    text_admin = ADMIN_COPY_TEMPLATE.format(
        name=data["name"],
        phone=data["phone"],
        category_h=CATEGORY_H[category],
        city=data["city"],
        description=data["description"],
        created_at=created_at,
    )

    try:
        # отправляем в канал
        msg = await c.bot.send_message(
            chat_id=channel_id,
            text=text_channel,
            reply_markup=claim_kb()
        )

        # сохраняем в БД (PostgreSQL)
        await save_request(
            message_id=msg.message_id,
            category=category,
            name=data["name"],
            phone=data["phone"],
            city=data["city"],
            description=data["description"],
        )

        # кэш в памяти
        active_requests[msg.message_id] = {
            "category": category,
            "user_id": None,
            "username": None,
        }

        # копия админу
        await c.bot.send_message(settings.OPERATOR_CHAT_ID, text_admin)

    except Exception as e:
        await c.message.answer(f"Ошибка публикации: {e}")
        await c.answer()
        return

    await state.clear()
    await c.message.edit_text(THANKS)
    await c.answer("Отправлено ✔")


# ----------------------------------------------------
# CLAIM (принятие заявки)
# ----------------------------------------------------

@router.callback_query(F.data == "req:claim")
async def claim_request(c: CallbackQuery):
    msg_id = c.message.message_id

    # Пытаемся взять из кэша
    req = active_requests.get(msg_id)

    # Если в кэше нет — пробуем достать из БД
    if not req:
        db_req = await get_request_by_message_id(msg_id)
        if not db_req:
            await c.answer("Заявка не найдена или устарела.", show_alert=True)
            return

        req = {
            "category": db_req["category"],
            "user_id": db_req.get("claimer_user_id"),
            "username": db_req.get("claimer_username"),
        }
        active_requests[msg_id] = req

    user = c.from_user
    uname = user.username or user.full_name or str(user.id)

    # если уже принята кем-то
    if req["user_id"]:
        if req["user_id"] == user.id:
            await c.answer("Вы уже приняли эту заявку.")
        else:
            await c.answer(f"Заявку уже взял @{req['username']}.", show_alert=True)
        return

    # устанавливаем владельца заявки (в кэше)
    req["user_id"] = user.id
    req["username"] = uname

    # сохраняем в БД владельца заявки
    await set_status_in_progress(
        msg_id,
        user.id,
        uname
    )


    # редактируем сообщение в канале
    new_text = (
        f"✅ Заявка принята в работу\n\n"
        f"{c.message.text}\n\n"
        f"👨‍💼 Принял: @{uname}"
    )
    try:
        await c.message.edit_text(new_text)
    except Exception:
        pass

    # генерируем короткий токен для dm_bot
    token = make_short_token(msg_id)

    # кнопка «Открыть диалог с ботом»
    kb = open_dm_external_kb(settings.BOT2_USERNAME, token)
    await c.message.edit_reply_markup(reply_markup=kb)

    await c.answer("Нажмите кнопку, чтобы получить заявку в ЛС.")


# ----------------------------------------------------
# BOOT
# ----------------------------------------------------

async def main():
    # Инициализируем БД (создаём таблицы, если их нет)
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logging.info(f"Bot #1 started as @{me.username} ({me.id})")

    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
