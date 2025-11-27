from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ..states import RequestForm
from ..config import settings, CATEGORY_TO_CHANNEL, CATEGORY_H
from ..db import save_request
from ..texts import THANKS, ADMIN_COPY_TEMPLATE, PUBLISHED_TEMPLATE
from ..keyboards import claim_kb, nav_kb
from ..utils import now_local_str

router = Router()

@router.callback_query(RequestForm.Confirm, F.data == "confirm:edit")
async def confirm_edit(c: CallbackQuery, state: FSMContext):
    await state.set_state(RequestForm.Description)
    await c.message.edit_text("Введите описание:", reply_markup=nav_kb())
    await c.answer()


@router.callback_query(RequestForm.Confirm, F.data == "confirm:send")
async def confirm_send(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    required = ["phone", "name", "category", "city", "description"]
    if not all(data.get(k) for k in required):
        return await c.answer("Не хватает данных", show_alert=True)

    category = data["category"]
    channel_id = CATEGORY_TO_CHANNEL.get(category)
    created_at = now_local_str()

    text_channel = PUBLISHED_TEMPLATE.format(
        name=data["name"],
        category_h=CATEGORY_H[category],
        city=data["city"],
        description=data["description"],
        created_at=created_at,
    )

    # текст админу
    text_admin = ADMIN_COPY_TEMPLATE.format(
        name=data["name"],
        phone=data["phone"],
        category_h=CATEGORY_H[category],
        city=data["city"],
        description=data["description"],
        created_at=created_at,
    )

    try:
        msg = await c.bot.send_message(
            chat_id=channel_id,
            text=text_channel,
            reply_markup=claim_kb()
        )
        await save_request(
            message_id=msg.message_id,
            category=category,
            name=data["name"],
            phone=data["phone"],
            city=data["city"],
            description=data["description"],
        )
        await c.bot.send_message(settings.OPERATOR_CHAT_ID, text_admin)

    except Exception as e:
        await c.message.answer(f"Ошибка публикации: {e}")
        return await c.answer()

    await state.clear()
    await c.message.edit_text(THANKS)
    await c.answer("✔ Отправлено")

def register_confirm_handlers(dp):
    dp.include_router(router)
