from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

SPECIALIZATIONS = {
    "Бухгалтер": "-1003247964016",
    "Адвокат": "-1003297330626",
    "EGOV": "-1003143756180"
}

def spec_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=spec, callback_data=f"spec:{spec}")]
        for spec in SPECIALIZATIONS.keys()
    ])
