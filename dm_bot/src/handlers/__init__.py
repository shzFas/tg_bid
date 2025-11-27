from aiogram import Dispatcher

from .start import register_start_handlers
from .claim import register_claim_handlers
from .cancel import register_cancel_handlers
from .done import register_done_handlers
from .tasks import register_tasks_handlers


def register_all_handlers(dp: Dispatcher):
    register_start_handlers(dp)
    register_claim_handlers(dp)
    register_cancel_handlers(dp)
    register_done_handlers(dp)
    register_tasks_handlers(dp)
