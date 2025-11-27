from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..utils.common import is_admin, HELP_TEXT

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    if is_admin(m.from_user.id):
        await m.answer(HELP_TEXT)

@router.message(Command("help"))
async def help_cmd(m: Message):
    if is_admin(m.from_user.id):
        await m.answer(HELP_TEXT)

@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    if is_admin(m.from_user.id):
        await state.clear()
        await m.answer("Операция отменена.")


def register_base_handlers(dp):
    dp.include_router(router)
