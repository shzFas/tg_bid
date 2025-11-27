from aiogram import Dispatcher

# --- Импорты роутеров ---
from .base import register_base_handlers
from .new_spec import register_new_spec_handlers
from .edit_spec import register_edit_handlers
from .list_specs import register_list_handlers
from .categories import register_categories_handlers
from .spec_view import router as router_spec_view
from .spec_categories import router as router_categories
from .invite import router as router_invite

def register_all_handlers(dp: Dispatcher):
    # --- старые функции регистрации ---
    register_base_handlers(dp)
    register_new_spec_handlers(dp)
    register_list_handlers(dp)
    register_edit_handlers(dp)
    register_categories_handlers(dp)

    # --- НОВЫЕ роутеры ---
    dp.include_router(router_spec_view)
    dp.include_router(router_categories)
    dp.include_router(router_invite)
