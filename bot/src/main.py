import asyncio, logging, hmac, hashlib
import redis.asyncio as redis

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from .config import settings, CATEGORY_TO_CHANNEL
from .states import RequestForm
from .keyboards import nav_kb, categories_kb, phone_kb, confirm_kb, claim_kb, open_dm_external_kb
from .texts import *
from .utils import preview_text, now_local_str

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
router = Router()

r: redis.Redis | None = None  # Redis клиент
active_requests: dict[int, dict] = {}  # в памяти держим минимум

def make_short_token(message_id: int) -> str:
    # token = "<hex(message_id)>.<HMAC-sha256(secret, hex)[:16]>"  -> <= ~40 символов
    mid_hex = format(message_id, "x")
    sig = hmac.new(settings.SHARED_SECRET.encode(), mid_hex.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{mid_hex}.{sig}"

def verify_short_token(token: str) -> int | None:
    try:
        mid_hex, sig = token.split(".", 2)
        expect = hmac.new(settings.SHARED_SECRET.encode(), mid_hex.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expect):
            return int(mid_hex, 16)
    except Exception:
        pass
    return None

# ===================== START =====================
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RequestForm.Phone)
    await m.answer(HELLO, reply_markup=phone_kb())
    await m.answer(ASK_PHONE, reply_markup=nav_kb())

# ===================== PHONE =====================
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
    text = m.text.strip()
    if len(text) < 6:
        await m.answer("Похоже, это не номер. Введите снова или отправьте контакт.", reply_markup=nav_kb())
        return
    await state.update_data(phone=text)
    await ask_name(m, state)

async def ask_name(m: Message, state: FSMContext):
    await state.set_state(RequestForm.Name)
    await m.answer(ASK_NAME, reply_markup=nav_kb())

# ===================== NAME =====================
@router.message(RequestForm.Name, F.text)
async def got_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(RequestForm.Category)
    await m.answer(ASK_CATEGORY, reply_markup=categories_kb())
    await m.answer("Выберите категорию кнопкой ниже ⤵️", reply_markup=ReplyKeyboardRemove())

@router.message(RequestForm.Category)
async def category_text_guard(m: Message, state: FSMContext):
    await m.answer("Пожалуйста, выберите категорию кнопкой 👇", reply_markup=categories_kb())

# ===================== CATEGORY =====================
@router.callback_query(RequestForm.Category, F.data.startswith("cat:"))
async def choose_category(c: CallbackQuery, state: FSMContext):
    _, cat = c.data.split(":", 1)
    await state.update_data(category=cat)
    await state.set_state(RequestForm.City)
    await c.message.edit_text(ASK_CITY, reply_markup=nav_kb())
    await c.answer()

# ===================== CITY =====================
@router.message(RequestForm.City, F.text)
async def got_city(m: Message, state: FSMContext):
    await state.update_data(city=m.text.strip())
    await state.set_state(RequestForm.Description)
    await m.answer(ASK_DESC, reply_markup=nav_kb())

# ===================== DESCRIPTION =====================
@router.message(RequestForm.Description, F.text)
async def got_desc(m: Message, state: FSMContext):
    await state.update_data(description=m.text.strip())
    data = await state.get_data()
    await state.set_state(RequestForm.Confirm)
    await m.answer(CONFIRM.format(preview=preview_text(data)), reply_markup=confirm_kb())

# ===================== NAVIGATION =====================
@router.callback_query(F.data == "nav:stop")
async def stop_flow(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(STOPPED)
    await c.answer()

@router.callback_query(F.data == "nav:cancel")
async def cancel_flow(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(CANCELED)
    await c.answer()

@router.callback_query(F.data == "nav:back")
async def go_back(c: CallbackQuery, state: FSMContext):
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

# ===================== CONFIRM =====================
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

    created_at = now_local_str()
    category = data["category"]
    channel_id = CATEGORY_TO_CHANNEL.get(category)
    if not channel_id:
        await c.answer("Канал для категории не настроен", show_alert=True)
        return

    text_channel = PUBLISHED_TEMPLATE.format(
        name=data["name"], category_h=CATEGORY_H[category],
        city=data["city"], description=data["description"], created_at=created_at
    )
    text_admin = ADMIN_COPY_TEMPLATE.format(
        name=data["name"], phone=data["phone"], category_h=CATEGORY_H[category],
        city=data["city"], description=data["description"], created_at=created_at
    )

    try:
        msg = await c.bot.send_message(chat_id=channel_id, text=text_channel, reply_markup=claim_kb())
        # Сохраним минимум в памяти
        active_requests[msg.message_id] = {
            "category": category, "user_id": None, "username": None, "channel_id": channel_id
        }
        # Полезную нагрузку для dm_bot положим в Redis
        payload = {
            "name": data["name"], "phone": data["phone"], "city": data["city"],
            "category_h": CATEGORY_H[category], "description": data["description"],
            "created_at": created_at,
        }
        await r.hset(f"claim:{msg.message_id}", mapping=payload)
        await r.expire(f"claim:{msg.message_id}", 86400)  # 1 день

        # копия админу
        await c.bot.send_message(chat_id=settings.OPERATOR_CHAT_ID, text=text_admin)
    except Exception as e:
        await c.message.answer(f"Не получилось опубликовать: {e}")
        await c.answer(); return

    await state.clear()
    try:
        await c.message.edit_text(THANKS)
    except:
        await c.message.answer(THANKS)
    await c.answer("Отправлено ✔")

# ===================== SPECIALISTS: claim =====================
@router.callback_query(F.data == "req:claim")
async def claim_request(c: CallbackQuery):
    msg_id = c.message.message_id
    req = active_requests.get(msg_id)
    if not req:
        await c.answer("Заявка не найдена или устарела.", show_alert=True); return

    user = c.from_user
    uname = user.username or user.full_name or str(user.id)

    if req["user_id"]:
        if req["user_id"] == user.id:
            await c.answer("Вы уже приняли эту заявку.")
        else:
            await c.answer(f"Эта заявка уже принята @{req['username']}.", show_alert=True)
        return

    req["user_id"] = user.id
    req["username"] = uname

    # отметим в канале и дадим кнопку на dm_bot
    new_text = (
        f"✅ Заявка принята в работу\n\n{c.message.text}\n\n👨‍💼 Принял: @{uname}"
    )
    try: await c.message.edit_text(new_text)
    except: pass

    token = make_short_token(msg_id)
    try:
        kb = open_dm_external_kb(settings.BOT2_USERNAME, token)
        await c.message.edit_reply_markup(reply_markup=kb)
    except: pass

    await c.answer("Нажмите кнопку, чтобы получить заявку в ЛС ✅")

# ===================== BOOT =====================
async def main():
    global r
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logging.info(f"Bot #1 started as @{me.username} ({me.id})")

    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
