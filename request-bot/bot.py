import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove
)
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from states import ReqForm
from keyboards import (
    phone_kb, category_kb, claim_kb,
    confirm_kb, edit_field_kb
)
from db import (
    save_request,
    save_message_id,
    request_already_claimed,
    check_approved_specialist,
    set_claimed,
    get_request_data,
)

load_dotenv()

REQUEST_BOT_TOKEN = os.getenv("REQUEST_BOT_TOKEN")
SPEC_BOT_TOKEN = os.getenv("SPEC_BOT_TOKEN")

bot = Bot(REQUEST_BOT_TOKEN)
spec_bot = Bot(SPEC_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

CHANNELS = {
    "ACCOUNTING": os.getenv("CHANNEL_ACCOUNTING"),
    "LAW": os.getenv("CHANNEL_LAW"),
    "EGOV": os.getenv("CHANNEL_EGOV")
}

# ======================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ: запомнить/очистить сообщения
# ======================================================

async def remember_msg(state: FSMContext, msg: Message):
    data = await state.get_data()
    ids = data.get("msg_ids", [])
    ids.append(msg.message_id)
    await state.update_data(msg_ids=ids)


async def cleanup_chat(state: FSMContext, msg: Message):
    data = await state.get_data()
    ids = data.get("msg_ids", [])
    chat_id = msg.chat.id

    for m_id in ids:
        try:
            await bot.delete_message(chat_id, m_id)
        except Exception:
            pass

    # очистим список сообщений в стейте
    await state.update_data(msg_ids=[])


async def show_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    preview = (
        "📄 <b>Проверьте вашу заявку:</b>\n\n"
        f"📞 Телефон: {data.get('phone', '—')}\n"
        f"👤 Имя: {data.get('name', '—')}\n"
        f"🏙 Город: {data.get('city', '—')}\n"
        f"📝 Описание: {data.get('desc', '—')}\n"
        f"📌 Категория: {data.get('category', '—')}\n\n"
        "Все верно?"
    )
    msg = await message.answer(preview, parse_mode="HTML", reply_markup=confirm_kb())
    await remember_msg(state, msg)


# ======================================================
# 1) START → FSM
# ======================================================

@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    q = await msg.answer("📞 Укажите номер телефона:", reply_markup=phone_kb())
    await remember_msg(state, msg)   # /start
    await remember_msg(state, q)
    await state.set_state(ReqForm.phone)


@dp.message(ReqForm.phone)
async def get_phone(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number if msg.contact else msg.text
    await state.update_data(phone=phone)
    await remember_msg(state, msg)

    data = await state.get_data()
    edit_field = data.get("edit_field")

    if edit_field == "phone":
        # редактировали только телефон → обратно к превью
        await state.update_data(edit_field=None)
        await show_preview(msg, state)
        return

    q = await msg.answer("👤 Как вас зовут?")
    await remember_msg(state, q)
    await state.set_state(ReqForm.name)


@dp.message(ReqForm.name)
async def get_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await remember_msg(state, msg)

    data = await state.get_data()
    edit_field = data.get("edit_field")

    if edit_field == "name":
        await state.update_data(edit_field=None)
        await show_preview(msg, state)
        return

    q = await msg.answer("🏙 Из какого вы города?")
    await remember_msg(state, q)
    await state.set_state(ReqForm.city)


@dp.message(ReqForm.city)
async def get_city(msg: Message, state: FSMContext):
    await state.update_data(city=msg.text)
    await remember_msg(state, msg)

    data = await state.get_data()
    edit_field = data.get("edit_field")

    if edit_field == "city":
        await state.update_data(edit_field=None)
        await show_preview(msg, state)
        return

    q = await msg.answer("📝 Опишите вашу проблему:")
    await remember_msg(state, q)
    await state.set_state(ReqForm.desc)


@dp.message(ReqForm.desc)
async def get_desc(msg: Message, state: FSMContext):
    await state.update_data(desc=msg.text)
    await remember_msg(state, msg)

    data = await state.get_data()
    edit_field = data.get("edit_field")

    if edit_field == "desc":
        await state.update_data(edit_field=None)
        await show_preview(msg, state)
        return

    q = await msg.answer("📌 Выберите категорию:", reply_markup=category_kb())
    await remember_msg(state, q)
    await state.set_state(ReqForm.category)


# 🔹 Выбор категории
@dp.callback_query(F.data.startswith("cat:"))
async def select_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    await state.update_data(category=category)

    data = await state.get_data()
    edit_field = data.get("edit_field")

    # если это редактирование категории → сразу к превью
    await state.update_data(edit_field=None)
    await show_preview(call.message, state)


# ======================================================
# 2) КНОПКИ: подтвердить / изменить
# ======================================================

@dp.callback_query(F.data == "confirm:send")
async def final_send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # сначала чистим чат
    await cleanup_chat(state, call.message)

    req_id = await save_request(data)
    channel_id = CHANNELS[data["category"]]

    msg = await bot.send_message(
        channel_id,
        f"📩 <b>Новая заявка (ID: {req_id})</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['desc']}",
        parse_mode="HTML",
        reply_markup=claim_kb(req_id)
    )

    await save_message_id(req_id, msg.message_id, channel_id)

    # одно финальное сообщение пользователю
    await call.message.answer(
        "✔ Ваша заявка отправлена! Скоро с вами свяжутся.",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()


@dp.callback_query(F.data == "confirm:edit")
async def edit_request(call: CallbackQuery):
    await call.message.answer("🔄 Что хотите изменить?", reply_markup=edit_field_kb())


# ======================================================
# 3) ОБРАБОТКА редактирования одного поля
# ======================================================

@dp.callback_query(F.data.startswith("edit:"))
async def edit_field(call: CallbackQuery, state: FSMContext):
    field = call.data.split(":")[1]

    # запомним, какое поле редактируем
    await state.update_data(edit_field=field)

    mapping = {
        "phone": ReqForm.phone,
        "name": ReqForm.name,
        "city": ReqForm.city,
        "desc": ReqForm.desc,
        "cat": ReqForm.category,
    }
    await state.set_state(mapping[field])

    questions = {
        "phone": "📞 Введите телефон:",
        "name": "👤 Введите имя:",
        "city": "🏙 Введите город:",
        "desc": "📝 Введите описание:",
        "cat": "📌 Выберите категорию:",
    }

    if field == "cat":
        q = await call.message.answer(questions[field], reply_markup=category_kb())
    else:
        q = await call.message.answer(questions[field])

    await remember_msg(state, call.message)
    await remember_msg(state, q)


# ======================================================
# 4) CLAIM — взятие заявки в работу
# ======================================================

@dp.callback_query(F.data.startswith("claim:"))
async def claim_request(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    tg_id = call.from_user.id
    username = call.from_user.username or f"id{tg_id}"

    if not await check_approved_specialist(tg_id):
        return await call.answer("⛔ Вы не одобрены как специалист!", show_alert=True)

    if await request_already_claimed(req_id):
        return await call.answer("❌ Заявку уже взял другой!", show_alert=True)

    await set_claimed(req_id, tg_id, username)
    data = await get_request_data(req_id)

    new_text = (
        f"📩 <b>Заявка (ID: {req_id})</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['description']}\n\n"
        f"✔ Взял: @{username}"
    )
    await bot.edit_message_text(
        new_text,
        chat_id=data["tg_chat_id"],
        message_id=data["tg_message_id"],
        parse_mode="HTML"
    )

    await spec_bot.send_message(
        tg_id,
        f"🛠 <b>Вы приняли заявку (ID: {req_id})</b>\n\n"
        f"📞 Телефон: {data['phone']}\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 {data['description']}\n"
        f"📌 Категория: {data['specialization']}",
        parse_mode="HTML"
    )

    await call.answer("👌 Вы взяли заявку!")


# ======================================================
# MAIN
# ======================================================

async def main():
    print("Request Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
