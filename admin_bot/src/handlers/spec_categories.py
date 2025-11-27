from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ..db import get_specialist_with_categories, set_specialist_categories
from ..keyboards import categories_kb
import html

router = Router()

@router.callback_query(F.data.startswith("spec_cat:open:"))
async def spec_cat_open(c: CallbackQuery, state: FSMContext):
    _, _, tg_id_str = c.data.split(":")
    tg_id = int(tg_id_str)

    spec = await get_specialist_with_categories(tg_id)
    if not spec:
        return await c.message.edit_text("❌ Специалист не найден")

    await state.update_data(tg_id=tg_id, categories=spec.get("categories") or [])

    text = (
        "📚 <b>Изменение категорий специалиста</b>\n\n"
        f"👤 <b>{html.escape(spec.get('full_name') or '-')}</b>\n"
        "Выберите категории:"
    )

    kb = categories_kb(selected=spec.get("categories") or [], mode="edit")
    await c.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("spec_cat:toggle:"))
async def spec_cat_toggle(c: CallbackQuery, state: FSMContext):
    parts = c.data.split(":")
    code = parts[2]  # LAW / ACCOUNTING / EGOV

    data = await state.get_data()
    selected = data.get("categories", [])

    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)

    await state.update_data(categories=selected)

    kb = categories_kb(selected=selected, mode="edit")
    await c.message.edit_reply_markup(reply_markup=kb)

@router.callback_query(F.data == "spec_cat:save")
async def spec_cat_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    categories = data.get("categories", [])

    await set_specialist_categories(tg_id, categories)
    await state.clear()

    cats_str = ", ".join(categories) or "—"

    await c.message.edit_text(
        f"✅ Категории обновлены: <code>{cats_str}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_view:{tg_id}")]]
        )
    )
