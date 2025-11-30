import os, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from dotenv import load_dotenv
from states import RequestForm
from keyboards import category_kb, CATEGORY_TO_CHANNEL
from db import save_request

load_dotenv()
bot = Bot(os.getenv("REQUEST_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.set_state(RequestForm.phone)
    await message.answer("📞 Укажите телефон:")

@dp.message(RequestForm.phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(RequestForm.name)
    await message.answer("👤 Укажите имя:")

@dp.message(RequestForm.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RequestForm.city)
    await message.answer("🏙 Укажите город:")

@dp.message(RequestForm.city)
async def get_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(RequestForm.description)
    await message.answer("📝 Опишите проблему:")

@dp.message(RequestForm.description)
async def get_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(RequestForm.specialization)
    await message.answer("Выберите категорию:", reply_markup=category_kb())

@dp.callback_query(F.data.startswith("cat:"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    await state.update_data(specialization=category, tg_chat_id=call.message.chat.id)
    data = await state.get_data()
    await save_request(data)      # Save to DB

    # 📨 SEND TO CHANNEL
    channel_id = CATEGORY_TO_CHANNEL[category]
    text = (
        f"🆕 <b>Новая заявка</b>\n\n"
        f"📞 Телефон: {data['phone']}\n"
        f"👤 Имя: {data['name']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📝 Описание: {data['description']}"
    )
    await bot.send_message(channel_id, text, parse_mode="HTML")

    await state.clear()
    try:
        for i in range(30): await bot.delete_message(call.message.chat.id, call.message.message_id - i)
    except: pass

    await bot.send_message(call.message.chat.id, "🎉 Заявка создана! Ожидайте ответа.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
