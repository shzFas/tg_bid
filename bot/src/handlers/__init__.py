from aiogram import Dispatcher

from .start import register_start_handlers
from .phone import register_phone_handlers
from .name import register_name_handlers
from .category import register_category_handlers
from .city import register_city_handlers
from .description import register_description_handlers
from .confirm import register_confirm_handlers
from .navigation import register_navigation_handlers
from .claim import register_claim_handlers


def register_all_handlers(dp: Dispatcher):
    register_start_handlers(dp)
    register_phone_handlers(dp)
    register_name_handlers(dp)
    register_category_handlers(dp)
    register_city_handlers(dp)
    register_description_handlers(dp)
    register_confirm_handlers(dp)
    register_navigation_handlers(dp)
    register_claim_handlers(dp)
