from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


CATEGORIES = [
    ("ACCOUNTING", "📊 Бухгалтерия"),
    ("LAW", "⚖️ Юрист"),
    ("EGOV", "🏛 EGOV"),
]


def categories_kb(selected: list[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура с переключателями категорий + сохранить/отмена.
    selected – список уже выбранных кодов категорий.
    """
    rows: list[list[InlineKeyboardButton]] = []

    # категории
    row: list[InlineKeyboardButton] = []
    for code, label in CATEGORIES:
        prefix = "✅ " if code in selected else "☑️ "
        row.append(
            InlineKeyboardButton(
                text=prefix + label,
                callback_data=f"new_spec:cat:{code}",
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
                text="✅ Сохранить",
                callback_data="new_spec:save",
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="new_spec:cancel",
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
