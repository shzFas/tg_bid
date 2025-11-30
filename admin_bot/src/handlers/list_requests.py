from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..db import get_requests_page

router = Router()
PAGE_SIZE = 5     # сколько заявок на одной странице


@router.message(F.text == "/requests")
async def open_requests_list_cmd(msg: Message):
    await send_requests_page(msg, page=1)


# ---------- 1. Кнопка для открытия списка ----------
@router.callback_query(F.data == "admin:requests")
async def open_requests_list(call: CallbackQuery):
    await send_requests_page(call, page=1)


# ---------- 2. Отрисовать страницу ----------
async def send_requests_page(call_or_message, page: int):
    rows, total = await get_requests_page(page, PAGE_SIZE)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    if not rows:
        return await call_or_message.answer("❌ Заявок нет")

    text = f"📄 <b>Заявки (стр. {page}/{pages}, всего: {total})</b>\n\n"
    kb_rows = []

    for r in rows:
        text += f"#{r['id']} | {r['name']} ({r['city']})\n"
        kb_rows.append([InlineKeyboardButton(
            text=f"✏️ Редактировать #{r['id']}",
            callback_data=f"req:menu:{r['message_id']}"
        )])

    # Пагинация ↓↓↓
    pag = []
    if page > 1:
        pag.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"req:page:{page - 1}"))
    if page < pages:
        pag.append(InlineKeyboardButton(text="Вперед ➡", callback_data=f"req:page:{page + 1}"))

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows + [pag] if pag else kb_rows)
    
    try:
        await call_or_message.message.edit_text(text, reply_markup=kb)
    except:
        await call_or_message.answer(text, reply_markup=kb)


# ---------- 3. Обработка страниц ----------
@router.callback_query(F.data.startswith("req:page:"))
async def list_page_handler(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    await send_requests_page(call, page)
    
def register_list_requests_handlers(dp):    
    dp.include_router(router)
