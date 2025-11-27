from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from ..utils.spec_service import build_specs_page
from ..db import get_specialists_list

router = Router()

@router.message(Command("list_specs"))
async def list_specs(m: Message):
    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, 1)
    await m.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("spec_list:"))
async def list_specs_page(c: CallbackQuery):
    page = int(c.data.split(":")[1])
    specs = await get_specialists_list()
    text, kb = build_specs_page(specs, page)
    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()

def register_list_handlers(dp):
    dp.include_router(router)
