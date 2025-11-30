from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

CATEGORIES = [
    ("ACCOUNTING", "📊 Бухгалтерия"),
    ("LAW", "⚖️ Юрист"),
    ("EGOV", "🏛 EGOV"),
]


def categories_kb(selected: list[str], mode: str = "new") -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура категорий.
    mode = "new" → new_spec:*
    mode = "edit" → spec_cat:*
    """
    prefix = "new_spec" if mode == "new" else "spec_cat"

    rows: list[list[InlineKeyboardButton]] = []

    # категории
    row: list[InlineKeyboardButton] = []
    for code, label in CATEGORIES:
        check = "✅ " if code in selected else "☑️ "
        row.append(
            InlineKeyboardButton(
                text=check + label,
                callback_data=f"{prefix}:toggle:{code}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # кнопки управления
    rows.append(
        [
            InlineKeyboardButton(
                text="💾 Сохранить",
                callback_data=f"{prefix}:save",
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"{prefix}:cancel",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)

def claim_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 Принять в работу", callback_data="req:claim")]
    ])

def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚕️ Специалисты", callback_data="admin:specs")],
        [InlineKeyboardButton(text="📄 Заявки", callback_data="admin:requests")],   # ← ВОТ ЭТО
    ])
