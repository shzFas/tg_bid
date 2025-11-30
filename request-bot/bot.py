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
from keyboards import phone_kb, category_kb, claim_kb
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
SPEC_BOT_TOKEN = os.getenv("SPEC_BOT_TOKEN")   # ⚠ второй бот для отправки в ЛС

bot = Bot(REQUEST_BOT_TOKEN)
spec_bot = Bot(SPEC_BOT_TOKEN)      # 👈 БОТ СПЕЦИАЛИСТОВ!

dp = Dispatcher(storage=MemoryStorage())


CHANNELS = {
    "ACCOUNTING": os.getenv("CHANNEL_ACCOUNTING"),
    "LAW": os.getenv("CHANNEL_LAW"),
    "EGOV": os.getenv("CHANNEL_EGOV")
}


# ======================================================
# 1) START → FSM
# ======================================================
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await msg.answer("📞 Укажите номер телефона:", reply_markup=phone_kb())
    await state.set_state(ReqForm.phone)


@dp.message(ReqForm.phone)
async def get_phone(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number if msg.contact else msg.text
    await state.update_data(phone=phone)

    await msg.answer("👤 Как вас зовут?")
    await state.set_state(ReqForm.name)


@dp.message(ReqForm.name)
async def get_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)

    await msg.answer("🏙 Из какого вы города?")
    await state.set_state(ReqForm.city)


@dp.message(ReqForm.city)
async def get_city(msg: Message, state: FSMContext):
    await state.update_data(city=msg.text)

    await msg.answer("📝 Опишите вашу проблему:")
    await state.set_state(ReqForm.desc)


@dp.message(ReqForm.desc)
async def get_desc(msg: Message, state: FSMContext):
    await state.update_data(desc=msg.text)

    await msg.answer("📌 Выберите категорию:", reply_markup=category_kb())
    await state.set_state(ReqForm.category)


# ======================================================
# 2) CATEGORY → отправляем в канал + БД
# ======================================================
@dp.callback_query(F.data.startswith("cat:"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    data = await state.get_data()
    data["category"] = category

    # 1. Сохранить в БД и получить ID
    req_id = await save_request(data)

    # 2. Сообщение в канал
    channel_id = CHANNELS[category]
    text = (
        f"📩 <b>Новая заявка (ID: {req_id})</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['desc']}\n\n"
        f"🛠 <b>Взять в работу</b>"
    )
    msg = await bot.send_message(
        channel_id,
        text,
        parse_mode="HTML",
        reply_markup=claim_kb(req_id)   # 👈 кнопка!
    )

    # 3. Сохраняем message_id и chat_id → для редактирования
    await save_message_id(req_id, msg.message_id, channel_id)

    # 4. Очистить FSM
    await call.message.answer(
        "✔ Ваша заявка отправлена! Скоро с вами свяжутся.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()


# ======================================================
# 3) CLAIM — берём в работу
# ======================================================
@dp.callback_query(F.data.startswith("claim:"))
async def claim_request(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    tg_id = call.from_user.id
    username = call.from_user.username or f"id{tg_id}"

    # 1) Проверить специалиста
    if not await check_approved_specialist(tg_id):
        return await call.answer("⛔ Вы не одобрены как специалист!", show_alert=True)

    # 2) Проверить, не взяли ли уже
    if await request_already_claimed(req_id):
        return await call.answer("❌ Заявку уже взял другой!", show_alert=True)

    # 3) Обновляем статус
    await set_claimed(req_id, tg_id, username)

    # 4) Данные заявки
    data = await get_request_data(req_id)

    # 5) Обновление в канале
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

    # 6) Отправляем данные специалисту В ЛС (через SPEC-BOT!)
    text_for_spec = (
        f"🛠 <b>Вы приняли заявку (ID: {req_id})</b>\n\n"
        f"📞 Телефон: {data['phone']}\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 {data['description']}\n"
        f"📌 Категория: {data['specialization']}"
    )
    await spec_bot.send_message(
        tg_id,
        text_for_spec,
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
