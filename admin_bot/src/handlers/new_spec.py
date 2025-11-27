from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..utils.common import is_admin
from ..keyboards import categories_kb
from ..states import NewSpecForm
from ..db import add_specialist, set_specialist_categories, get_specialist_with_categories

router = Router()

@router.message(Command("new_spec"))
async def new_spec_start(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    await state.clear()
    await state.update_data(mode="new")
    await state.set_state(NewSpecForm.WaitingForTgId)
    await m.answer("➕ <b>Добавление нового специалиста</b>\nВведите tg_id:")


@router.message(NewSpecForm.WaitingForTgId)
async def spec_got_tg_id(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    try:
        tg_id = int(m.text.strip())
    except:
        return await m.answer("tg_id должен быть числом")

    await state.update_data(tg_id=tg_id)
    await state.set_state(NewSpecForm.WaitingForFullName)
    await m.answer("Введите ФИО специалиста:")


@router.message(NewSpecForm.WaitingForFullName)
async def spec_got_full_name(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return

    full_name = m.text.strip()
    if not full_name:
        return await m.answer("ФИО слишком короткое")

    data = await state.get_data()
    tg_id = data["tg_id"]

    try:
        chat = await m.bot.get_chat(tg_id)
        username = chat.username or None
    except:
        username = None

    await state.update_data(full_name=full_name, username=username)
    await state.set_state(NewSpecForm.ChoosingCategories)

    await m.answer("Выберите категории:", reply_markup=categories_kb([], mode="new"))


@router.callback_query(NewSpecForm.ChoosingCategories, F.data.startswith("new_spec:toggle:"))
async def new_spec_toggle(c: CallbackQuery, state: FSMContext):
    _, _, cat = c.data.split(":")
    data = await state.get_data()
    selected = data.get("categories", [])

    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)

    await state.update_data(categories=selected)
    await c.message.edit_reply_markup(reply_markup=categories_kb(selected, mode="new"))
    await c.answer()


@router.callback_query(NewSpecForm.ChoosingCategories, F.data == "new_spec:save")
async def new_spec_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = data["tg_id"]
    full_name = data["full_name"]
    username = data["username"]
    categories = data["categories"]

    await add_specialist(tg_user_id=tg_id, username=username, full_name=full_name)
    await set_specialist_categories(tg_id, categories)

    await state.clear()
    await c.message.edit_text(f"✅ Добавлен:\n<b>{full_name}</b>\nКатегории: {', '.join(categories)}")
    await c.answer()


def register_new_spec_handlers(dp):
    dp.include_router(router)
