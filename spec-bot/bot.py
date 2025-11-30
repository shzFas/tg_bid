import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove
)

from dotenv import load_dotenv

from states import SpecReg
from keyboards import (
    phone_kb,
    spec_multi_kb,
    cancel_request_kb,
    done_request_kb
)
from db import (
    specialist_exists,
    save_specialist,
    is_approved_specialist,
    get_claimed_requests,
    cancel_request,
    complete_request
)

load_dotenv()
bot = Bot(os.getenv("SPEC_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

PAGE_SIZE = 5


# =========================================================
# 1) РЕГИСТРАЦИЯ СПЕЦИАЛИСТА
# =========================================================
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    tg_id = message.from_user.id

    if await specialist_exists(tg_id):
        return await message.answer(
            "⚠️ Вы уже отправили заявку.\n"
            "⏳ Ожидайте подтверждения администратора."
        )

    await state.set_state(SpecReg.name)
    await message.answer("👋 Введите ваше имя:")


@dp.message(SpecReg.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(SpecReg.phone)

    await message.answer(
        "📞 Введите телефон или нажмите кнопку:",
        reply_markup=phone_kb()
    )


@dp.message(SpecReg.phone)
async def get_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = None if message.text.lower() == "нет" else message.text

    await state.update_data(phone=phone, specialization=[])
    await state.set_state(SpecReg.specialization)

    await message.answer(
        "🛠 Выберите специализации (можно несколько):",
        reply_markup=spec_multi_kb([])
    )


@dp.callback_query(F.data.startswith("toggle:"))
async def toggle_spec(call: CallbackQuery, state: FSMContext):
    spec = call.data.split(":")[1]
    data = await state.get_data()
    selected: list = data.get("specialization", [])

    if spec in selected:
        selected.remove(spec)
    else:
        selected.append(spec)

    await state.update_data(specialization=selected)
    await call.message.edit_reply_markup(reply_markup=spec_multi_kb(selected))


@dp.callback_query(F.data == "done")
async def finalize(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    specs = data.get("specialization", [])

    if not specs:
        return await call.answer("❗ Выберите хотя бы одну специальность", show_alert=True)

    tg_user = call.from_user
    username = tg_user.username or f"id{tg_user.id}"

    await save_specialist(tg_user.id, username, data)
    await state.clear()

    try:
        for i in range(20):
            await bot.delete_message(call.message.chat.id, call.message.message_id - i)
    except:
        pass

    await bot.send_message(
        tg_user.id,
        "📝 Заявка на специалиста отправлена!\n"
        "⏳ Ожидайте подтверждения администратора.",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================================================
# 2) ПРОСМОТР СВОИХ ЗАЯВОК  /my_requests
# =========================================================
@dp.message(Command("my_requests"))
async def my_requests(message: Message):
    tg_id = message.from_user.id

    if not await is_approved_specialist(tg_id):
        return await message.answer("⛔ Вы не одобрены администратором.")

    requests, total_pages = await get_claimed_requests(tg_id, 1, PAGE_SIZE)

    if not requests:
        return await message.answer("📭 У вас нет заявок в работе.")

    for r in requests:
        text = (
            f"🔹 <b>ID:</b> {r['id']}\n"
            f"📞 <b>Телефон клиента:</b> {r['phone']}\n"
            f"📝 <b>Описание:</b> {r['description']}\n"
            f"📌 <b>Статус:</b> {r['status']}"
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=done_request_kb(r["id"], cancel=True)
        )


# =========================================================
# 3) CALLBACK — отмена заявки
# =========================================================
@dp.callback_query(F.data.startswith("cancel:"))
async def cancel_request_cb(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    tg_id = call.from_user.id

    ok = await cancel_request(req_id, tg_id)

    if ok:
        await call.answer("🔄 Заявка возвращена в PENDING")
        await call.message.edit_text("🔄 Заявка отменена (теперь PENDING)")
    else:
        await call.answer("❌ Вы не можете отменить эту заявку", show_alert=True)


# =========================================================
# 4) CALLBACK — заявка выполнена (“DONE”)
# =========================================================
@dp.callback_query(F.data.startswith("done:"))
async def done_request_cb(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    tg_id = call.from_user.id

    ok = await complete_request(req_id, tg_id)

    if ok:
        await call.answer("✔ Заявка выполнена!")
        await call.message.edit_text("🎉 Заявка отмечена как DONE.")
    else:
        await call.answer("❌ Это не ваша заявка или ошибка.", show_alert=True)


# =========================================================
# MAIN
# =========================================================
async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
