from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ⚠ Эти ID ты уже использовал
CATEGORY_TO_CHANNEL = {
    "Бухгалтер": -1003247964016,
    "Адвокат": -1003297330626,
    "EGOV": -1003143756180
}

def category_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=spec, callback_data=f"cat:{spec}")]
        for spec in CATEGORY_TO_CHANNEL.keys()
    ])
