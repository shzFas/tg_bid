import html
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..config import CATEGORY_H

def fmt_payload(row: dict) -> str:
    category_h = CATEGORY_H.get(row["category"], row["category"])
    return (
        f"📄 <b>Заявка клиента:</b>\n\n"
        f"👤 Имя: {row['name']}\n"
        f"📞 Телефон: <code>{row['phone']}</code>\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙️ Город: {row['city']}\n"
        f"📝 {row['description']}\n"
        f"🕒 {row['created_at']}\n\n"
        f"Теперь вы можете связаться с клиентом."
    )

def task_kb(message_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{message_id}"),
        InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{message_id}"),
    ]])
