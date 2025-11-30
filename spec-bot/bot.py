import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from dotenv import load_dotenv

from states import SpecReg
from keyboards import spec_kb
from db import save_specialist, specialist_exists

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    """Начало регистрации"""
    tg_id = message.from_user.id
    if await specialist_exists(tg_id):
        return await message.answer(
            "⚠️ Вы уже отправили заявку. Ожидайте проверки администратора."
        )

    await state.set_state(SpecReg.name)
    await message.answer("👋 Привет! Введите ваше имя:")


@dp.message(SpecReg.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(SpecReg.phone)
    await message.answer("📞 Введите телефон (или напишите `нет`):")


@dp.message(SpecReg.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = None if message.text.lower() == "нет" else message.text
    await state.update_data(phone=phone)
    await state.set_state(SpecReg.specialization)
    await message.answer("🔧 Выберите специализацию:", reply_markup=spec_kb())


@dp.callback_query(F.data.startswith("spec:"))
async def get_specialization(call: CallbackQuery, state: FSMContext):
    spec = call.data.split(":")[1]
    tg_user = call.from_user
    username = tg_user.username or f"id{tg_user.id}"

    await state.update_data(specialization=[spec])
    data = await state.get_data()

    await save_specialist(tg_user.id, username, data)
    await state.clear()

    # Чистим последние сообщения
    try:
        for i in range(20):
            await bot.delete_message(call.message.chat.id, call.message.message_id - i)
    except:
        pass

    await bot.send_message(
        tg_user.id,
        "📝 Ваша заявка отправлена!\n"
        "⏳ Ожидайте подтверждения администратора."
    )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
