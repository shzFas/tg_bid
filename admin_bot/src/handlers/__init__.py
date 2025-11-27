from aiogram import Dispatcher

from .base import register_base_handlers
from .new_spec import register_new_spec_handlers
from .list_specs import register_list_handlers
from .edit_spec import register_edit_handlers
from .categories import register_categories_handlers
from .invite import register_invite_handlers


def register_all_handlers(dp: Dispatcher):
    register_base_handlers(dp)
    register_new_spec_handlers(dp)
    register_list_handlers(dp)
    register_edit_handlers(dp)
    register_categories_handlers(dp)
    register_invite_handlers(dp)
