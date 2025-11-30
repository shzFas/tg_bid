from ..config import settings

def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list

HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/new_spec</code> – добавить нового специалиста\n"
    "<code>/list_specs</code> – список всех специалистов\n"
    "<code>/requests</code> – список всех заявок\n"
)
