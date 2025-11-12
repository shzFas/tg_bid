from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

def nav_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back"),
        InlineKeyboardButton(text="⛔ Стоп", callback_data="nav:stop"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="nav:cancel"),
    ]])

def categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бухгалтер", callback_data="cat:ACCOUNTING")],
        [InlineKeyboardButton(text="Адвокат", callback_data="cat:LAW")],
        [InlineKeyboardButton(text="EGOV", callback_data="cat:EGOV")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back"),
         InlineKeyboardButton(text="⛔ Стоп", callback_data="nav:stop")]
    ])

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def remove_kb():
    return ReplyKeyboardRemove()

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm:send")],
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm:edit"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="nav:cancel"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")]
    ])

def claim_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 Принять в работу", callback_data="req:claim")]
    ])
