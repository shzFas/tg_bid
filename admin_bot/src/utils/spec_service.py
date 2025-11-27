import html
import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 5

def build_specs_page(specs: list[dict], page: int):
    total = len(specs)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    page = max(1, min(page, pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = specs[start:end]

    lines = [f"📋 <b>Список специалистов</b> ({page}/{pages})\n"]
    buttons = []

    for s in chunk:
        full_name = html.escape(s["full_name"] or "-")
        cats = ", ".join(s.get("categories") or [])

        buttons.append([InlineKeyboardButton(
            text=f"📄 {full_name}",
            callback_data=f"spec_view:{s['tg_user_id']}"
        )])

        lines.append(f"<b>{full_name}</b>\n<code>{cats}</code>\n")

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"spec_list:{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"spec_list:{page+1}"))

    if nav:
        buttons.append(nav)

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)
