from ..config import settings

def is_admin(uid: int) -> bool:
    return uid in settings.admin_ids_list

HELP_TEXT = (
    "🔐 <b>Админ-бот – список команд</b>\n\n"
    "<b>👨‍⚖ Управление специалистами:</b>\n"
    "<code>/new_spec</code> – добавить нового специалиста\n"
    "<code>/edit_spec tg_id</code> – изменить данные специалиста\n"
    "<code>/list_specs</code> – список всех специалистов\n"
    "<code>/invite_spec tg_id</code> – ссылки в каналы\n"
    "<code>/notify_spec tg_id</code> – отправить ссылки специалисту\n\n"
)
