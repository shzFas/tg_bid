from datetime import datetime
from .texts import CATEGORY_H

def now_local_str():
    return datetime.now().strftime("%d.%m.%Y, %H:%M")

def preview_text(data: dict) -> str:
    return (
        f"👤 Имя: {data.get('name')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"⚖️ Специалист: {CATEGORY_H.get(data.get('category',''), data.get('category',''))}\n"
        f"🏙️ Город: {data.get('city')}\n"
        f"📝 Проблема: {data.get('description')}"
    )
