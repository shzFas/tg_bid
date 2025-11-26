from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)

def claim_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 Принять в работу", callback_data="req:claim")]
    ])
    
def open_dm_external_kb(bot2_username: str, token: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📩 Открыть диалог с ботом",
            url=f"https://t.me/{bot2_username}?start={token}"
        )]
    ])

