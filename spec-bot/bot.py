import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from dotenv import load_dotenv

from states import SpecReg, CancelNote
from keyboards import (
    phone_kb,
    spec_multi_kb,
    request_action_kb
)
from db import (
    specialist_exists,
    save_specialist,
    is_approved_specialist,
    get_claimed_requests,
    cancel_request,
    complete_request,
    get_request_data,
    save_cancel_note
)

load_dotenv()
bot = Bot(os.getenv("SPEC_BOT_TOKEN"))
request_bot = Bot(os.getenv("REQUEST_BOT_TOKEN"))   # ДЛЯ ОБНОВЛЕНИЯ КАНАЛА!

dp = Dispatcher(storage=MemoryStorage())
PAGE_SIZE = 5
CHANNELS = {
    "ACCOUNTING": os.getenv("CHANNEL_ACCOUNTING"),
    "LAW": os.getenv("CHANNEL_LAW"),
    "EGOV": os.getenv("CHANNEL_EGOV"),
}

# ====================== РЕГИСТРАЦИЯ ======================
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    tg_id = message.from_user.id

    if await specialist_exists(tg_id):
        return await message.answer(
            "⚠️ Вы уже отправили заявку.\n⏳ Ожидайте подтверждения."
        )

    await state.set_state(SpecReg.name)
    await message.answer("👋 Введите ваше имя:")


@dp.message(SpecReg.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(SpecReg.phone)
    await message.answer("📞 Телефон:", reply_markup=phone_kb())


@dp.message(SpecReg.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
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
    selected = data.get("specialization", [])

    if spec in selected: selected.remove(spec)
    else: selected.append(spec)

    await state.update_data(specialization=selected)
    await call.message.edit_reply_markup(reply_markup=spec_multi_kb(selected))


@dp.callback_query(F.data == "done_specs")
async def finalize(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("specialization"):
        return await call.answer("❗ Выберите хотя бы одну", show_alert=True)

    tg_user = call.from_user
    username = tg_user.username or f"id{tg_user.id}"

    await save_specialist(tg_user.id, username, data)
    await state.clear()

    await bot.send_message(tg_user.id, "📝 Заявка отправлена, ждите подтверждения!")
    await call.message.delete()


# ====================== ПАГИНАЦИЯ ЗАЯВОК ======================
@dp.message(Command("my_requests"))
async def my_requests(message: Message):
    tg_id = message.from_user.id
    if not await is_approved_specialist(tg_id):
        return await message.answer("⛔ Вы не одобрены администратором.")

    requests, total_pages = await get_claimed_requests(tg_id, 1, PAGE_SIZE)

    if not requests:
        return await message.answer("📭 Заявок пока нет.")

    for r in requests:
        text = (
            f"🆔 <b>ID:</b> {r['id']}\n"
            f"📞 <b>Телефон:</b> {r['phone']}\n"
            f"🏙 <b>Город:</b> {r['city']}\n"
            f"📝 <b>Описание:</b> {r['description']}\n"
            f"🚦 <b>Статус:</b> {r['status']}"
        )
        if r.get("cancel_note"):
            text += f"\n❗ <b>Причина отмены:</b> {r['cancel_note']}"

        await message.answer(text, parse_mode="HTML",
                             reply_markup=request_action_kb(r["id"]))


# ====================== ОТМЕНА ЗАЯВКИ ======================
@dp.callback_query(F.data.startswith("cancel:"))
async def cancel_request_cb(call: CallbackQuery, state: FSMContext):
    req_id = int(call.data.split(":")[1])
    await state.update_data(req_id=req_id)
    await state.set_state(CancelNote.note)
    await call.message.answer("📝 Укажите причину отмены (или '-' если без причины):")


@dp.message(CancelNote.note)
async def save_cancel_note_cb(message: Message, state: FSMContext):
    data = await state.get_data()
    req_id = data["req_id"]
    note = message.text

    ok = await save_cancel_note(req_id, message.from_user.id, note)

    if ok:
        # ========== 🔄 ОБНОВЛЕНИЕ КАНАЛА ==========
        req = await get_request_data(req_id)
        channel_id = req['tg_chat_id']

        text = (
            f"📩 <b>Заявка (ID: {req_id})</b>\n\n"
            f"👤 Имя: {req['name']}\n"
            f"🏙 {req['city']}\n"
            f"📝 {req['description']}\n"
            f"❌ <b>Отменено специалистом</b>\n"
        )
        if note != "-":
            text += f"\n⚠️ Причина: <i>{note}</i>\n\n"

        # заново – кнопка взять в работу
        await request_bot.edit_message_text(
            text,
            chat_id=channel_id,
            message_id=req["tg_message_id"],
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(
                    text="⚒ Взять в работу", callback_data=f"claim:{req_id}"
                )]]
            )
        )

        await message.answer("🔄 Заявка отменена и возвращена в канал!")
        await state.clear()

    else:
        await message.answer("❌ Ошибка, заявка не ваша")


# ====================== DONE ======================
@dp.callback_query(F.data.startswith("done:"))
async def done_request_cb(call: CallbackQuery):
    req_id = int(call.data.split(":")[1])
    tg_id = call.from_user.id

    ok = await complete_request(req_id, tg_id)

    if ok:
        await call.answer("✔ Заявка выполнена!")
        await call.message.edit_text("🎉 Заявка отмечена как DONE")
    else:
        await call.answer("❌ Ошибка", show_alert=True)


async def main():
    print("SPEC-BOT started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
