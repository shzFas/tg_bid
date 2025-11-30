from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from ..states import EditRequestState
from ..db import get_request_by_message_id, update_request
from ..config import CATEGORY_TO_CHANNEL

router = Router()

# --- 📌 Открываем меню редактирования заявки ---
@router.callback_query(F.data.startswith("req:menu:"))
async def open_edit_menu(call: CallbackQuery):
    message_id = int(call.data.split(":")[2])

    req = await get_request_by_message_id(message_id)
    if not req:
        return await call.answer("❌ Не найдено (может заявка уже перенаправлена?)")

    txt = (
        f"<b>Заявка #{req['id']}</b>\n"
        f"👤 Имя: {req['name']}\n"
        f"📞 Телефон: {req['phone']}\n"
        f"🏙 Город: {req['city']}\n"
        f"💬 Описание:\n{req['description']}\n\n"
        f"📂 Категория: <b>{req['category']}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"req:edit_desc:{message_id}")],
        [InlineKeyboardButton(text="📞 Изменить телефон", callback_data=f"req:edit_phone:{message_id}")],
        [InlineKeyboardButton(text="🏙 Изменить город", callback_data=f"req:edit_city:{message_id}")],
        [InlineKeyboardButton(text="🔄 Перенаправить", callback_data=f"req:redir:{message_id}")],
        [InlineKeyboardButton(text="🗑 Удалить заявку", callback_data=f"req:delete:{message_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="admin:requests")],
    ])

    await call.message.edit_text(txt, reply_markup=kb)
    
@router.callback_query(F.data.startswith("req:edit_desc:"))
async def edit_desc_start(call: CallbackQuery, state: FSMContext):
    msg_id = int(call.data.split(":")[2])
    await state.update_data(msg_id=msg_id)
    await state.set_state(EditRequestState.wait_desc)

    await call.message.answer("✏️ Введи НОВОЕ описание:")


# --- Сохраняем описание ---
@router.message(EditRequestState.wait_desc)
async def edit_desc_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["msg_id"]

    # найдём заявку
    from ..db import get_request_by_message_id, update_request
    req = await get_request_by_message_id(msg_id)
    if not req:
        await msg.answer("❌ Заявка не найдена.")
        return

    # новое описание + отметка
    new_text = f"{msg.text}\n\n🛠 Изменено @{msg.from_user.username} ({datetime.now().strftime('%d.%m %H:%M')})"
    await update_request(req["id"], {"description": new_text})

    await state.clear()
    await msg.answer("✔ Описание обновлено!")

@router.callback_query(F.data.startswith("req:edit_phone:"))
async def edit_phone_start(call: CallbackQuery, state: FSMContext):
    msg_id = int(call.data.split(":")[2])
    await state.update_data(msg_id=msg_id)
    await state.set_state(EditRequestState.wait_phone)

    await call.message.answer("📞 Введи НОВЫЙ телефон:")


@router.message(EditRequestState.wait_phone)
async def edit_phone_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["msg_id"]

    from ..db import get_request_by_message_id, update_request
    req = await get_request_by_message_id(msg_id)
    if not req:
        await msg.answer("❌ Заявка не найдена.")
        return

    await update_request(req["id"], {"phone": msg.text})
    await state.clear()
    await msg.answer("✔ Телефон обновлён!")

@router.callback_query(F.data.startswith("req:edit_city:"))
async def edit_city_start(call: CallbackQuery, state: FSMContext):
    msg_id = int(call.data.split(":")[2])
    await state.update_data(msg_id=msg_id)
    await state.set_state(EditRequestState.wait_city)

    await call.message.answer("🏙 Введи НОВЫЙ город:")


@router.message(EditRequestState.wait_city)
async def edit_city_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["msg_id"]

    from ..db import get_request_by_message_id, update_request
    req = await get_request_by_message_id(msg_id)
    if not req:
        await msg.answer("❌ Заявка не найдена.")
        return

    await update_request(req["id"], {"city": msg.text})
    await state.clear()
    await msg.answer("✔ Город обновлён!")

@router.callback_query(F.data.startswith("req:edit_cat:"))
async def edit_cat_start(call: CallbackQuery, state: FSMContext):
    msg_id = int(call.data.split(":")[2])
    await state.update_data(msg_id=msg_id)
    await state.set_state(EditRequestState.wait_cat)

    await call.message.answer("🧠 Введи категорию (ACCOUNTING / LAW / EGOV):")


@router.message(EditRequestState.wait_cat)
async def edit_cat_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["msg_id"]

    if msg.text not in ["ACCOUNTING", "LAW", "EGOV"]:
        return await msg.answer("⚠ Неверная категория. Попробуй снова.")

    from ..db import get_request_by_message_id, update_request
    req = await get_request_by_message_id(msg_id)
    if not req:
        return await msg.answer("❌ Заявка не найдена.")

    await update_request(req["id"], {"category": msg.text})
    await state.clear()
    await msg.answer(f"✔ Категория обновлена на <b>{msg.text}</b>!")

@router.callback_query(F.data.startswith("req:redir:"))
async def redirect_request_choose_category(call: CallbackQuery):
    msg_id = int(call.data.split(":")[2])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ACCOUNTING", callback_data=f"req:go:ACCOUNTING:{msg_id}")],
        [InlineKeyboardButton(text="LAW",        callback_data=f"req:go:LAW:{msg_id}")],
        [InlineKeyboardButton(text="EGOV",       callback_data=f"req:go:EGOV:{msg_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"req:menu:{msg_id}")],
    ])

    await call.message.edit_text("🔄 Выбери канал для перенаправления:", reply_markup=kb)
    
@router.callback_query(F.data.startswith("req:go:"))
async def redirect_request_execute(call: CallbackQuery, bot):
    _, _, new_cat, msg_id = call.data.split(":")
    msg_id = int(msg_id)

    from ..db import get_request_by_message_id, update_request
    req = await get_request_by_message_id(msg_id)

    old_channel = CATEGORY_TO_CHANNEL.get(req["category"])
    new_channel = CATEGORY_TO_CHANNEL.get(new_cat)

    # --- Удаляем старое сообщение
    try:
        await bot.delete_message(old_channel, msg_id)
    except:
        pass

    text = (
        f"{new_cat}\n"
        f"🔄 Заявка перенаправлена\n\n"
        f"👤 Имя: {req['name']}\n"
        f"📞 Тел: <code>{req['phone']}</code>\n"
        f"🏙 Город: {req['city']}\n"
        f"💬 Описание:\n{req['description']}\n\n"
        f"⚒ Изменено @{call.from_user.username} ({datetime.now().strftime('%d.%m %H:%M')})"
    )

    # <<<  ТУТ ГЛАВНОЕ  >>>
    from ..keyboards import claim_kb
    new_msg = await bot.send_message(
        chat_id=new_channel,
        text=text,
        reply_markup=claim_kb()  # <<< КНОПКА ПОЯВИТСЯ В КАНАЛЕ
    )

    # --- Обновляем БД
    await update_request(req['id'], {
        "message_id": new_msg.message_id,
        "category": new_cat
    })

    await call.message.answer(f"✔ Отправлено в {new_cat} с кнопкой!")

@router.callback_query(F.data.startswith("req:delete:"))
async def delete_request(call: CallbackQuery, bot):
    msg_id = int(call.data.split(":")[2])

    from ..db import get_request_by_message_id, delete_request_by_id
    req = await get_request_by_message_id(msg_id)

    if not req:
        return await call.answer("❌ Заявка не найдена", show_alert=True)

    # удаляем из БД
    await delete_request_by_id(req["id"])

    # удаляем из канала
    try:
        channel_id = CATEGORY_TO_CHANNEL.get(req["category"])
        await bot.delete_message(channel_id, msg_id)
    except Exception as e:
        print("Ошибка удаления из канала:", e)

    await call.message.answer("🗑 Заявка удалена полностью!")
