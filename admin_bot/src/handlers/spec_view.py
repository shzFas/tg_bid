from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import html

from ..db import get_specialist_with_categories
from ..config import CATEGORY_TO_CHANNEL, settings

router = Router()

@router.callback_query(F.data.startswith("spec_view:"))
async def view_spec_card(c: CallbackQuery):
    _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    full_name = html.escape(spec.get("full_name") or "-")
    username = html.escape(spec.get("username") or "-")
    cats = ", ".join(spec.get("categories") or []) or "—"

    text = (
        "📄 <b>Карточка специалиста</b>\n\n"
        f"👤 <b>ФИО:</b> {full_name}\n"
        f"💬 <b>username:</b> @{username}\n"
        f"🆔 <b>tg_id:</b> <code>{tg_id}</code>\n"
        f"📚 <b>Категории:</b> <code>{cats}</code>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Категории", callback_data=f"spec_cat:open:{tg_id}")],
            [InlineKeyboardButton(text="✏️ Редактировать ФИО", callback_data=f"spec_edit:{tg_id}")],
            [InlineKeyboardButton(text="🔗 Каналы", callback_data=f"spec_invite:{tg_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="spec_back_to_list")]
        ]
    )

    await c.message.edit_text(text, reply_markup=kb)
