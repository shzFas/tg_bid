from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def category_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Бухгалтерия", callback_data="cat:ACCOUNTING")],
        [InlineKeyboardButton(text="⚖️ Адвокат", callback_data="cat:LAW")],
        [InlineKeyboardButton(text="🏛 EGOV", callback_data="cat:EGOV")],
    ])

def claim_kb(req_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Взять в работу", callback_data=f"claim:{req_id}")]
    ])