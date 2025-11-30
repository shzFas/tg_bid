from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

SPECIALIZATIONSBTN = ["ACCOUNTING", "LAW", "EGOV"]

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Отправить номер", request_contact=True)],
            [KeyboardButton(text="✍️ Ввести вручную")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def spec_multi_kb(selected: list[str]):
    kb = []
    for spec in SPECIALIZATIONSBTN:
        check = "✔" if spec in selected else " "
        kb.append([InlineKeyboardButton(text=f"{check} {spec}", callback_data=f"toggle:{spec}")])

    kb.append([InlineKeyboardButton(text="🟢 Готово", callback_data="done")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def cancel_request_kb(request_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить заявку", callback_data=f"cancel:{request_id}")]
    ])
    
def done_request_kb(req_id: int, cancel: bool = True):
    kb = [
        [InlineKeyboardButton(text="✔ Выполнено", callback_data=f"done:{req_id}")]
    ]
    if cancel:
        kb.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{req_id}")])

    return InlineKeyboardMarkup(inline_keyboard=kb)