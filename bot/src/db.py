import asyncpg
from typing import Optional, Dict, Any, List

from .config import settings
from .keyboards import claim_kb

_pool: Optional[asyncpg.Pool] = None


# -------------------------------------------------------------------------
#  DB INIT
# -------------------------------------------------------------------------

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=5,
        )
    return _pool


async def init_db() -> None:
    """
    Инициализация таблиц И добавление недостающих колонок.
    Это ОДИН РАЗ вызывается при старте ботов.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Создать таблицу
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id               BIGSERIAL PRIMARY KEY,
                message_id       BIGINT UNIQUE NOT NULL,
                category         TEXT NOT NULL,
                name             TEXT NOT NULL,
                phone            TEXT NOT NULL,
                city             TEXT NOT NULL,
                description      TEXT NOT NULL,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                -- текущий статус заявки
                status           TEXT NOT NULL DEFAULT 'PENDING',

                -- кто взял в работу
                claimer_user_id  BIGINT,
                claimer_username TEXT,

                -- если отменили
                cancel_comment   TEXT,

                -- если завершили
                archived_at      TIMESTAMPTZ
            );
            """
        )

        # Абсолютно безопасные ALTER — если колонка есть, пропускается
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PENDING';"
        )
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS cancel_comment TEXT;"
        )
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;"
        )
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS claimer_user_id BIGINT;"
        )


# -------------------------------------------------------------------------
#  BOT #1 — СОХРАНЕНИЕ НОВОЙ ЗАЯВКИ
# -------------------------------------------------------------------------

async def save_request(
    *,
    message_id: int,
    category: str,
    name: str,
    phone: str,
    city: str,
    description: str,
) -> int:
    """
    Сохраняет заявку в БД.
    Если такая message_id есть — обновляет данные.
    Возвращает id записи.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO requests (
                message_id, category, name, phone, city, description
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (message_id) DO UPDATE
                SET category    = EXCLUDED.category,
                    name        = EXCLUDED.name,
                    phone       = EXCLUDED.phone,
                    city        = EXCLUDED.city,
                    description = EXCLUDED.description
            RETURNING id;
            """,
            message_id,
            category,
            name,
            phone,
            city,
            description,
        )
        return row["id"]


# -------------------------------------------------------------------------
#  CRUD — ОБЩИЕ ФУНКЦИИ
# -------------------------------------------------------------------------

async def get_request_by_message_id(message_id: int) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1;",
            message_id,
        )
        return dict(row) if row else None


async def set_status_in_progress(message_id: int, user_id: int, username: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET status = 'IN_PROGRESS',
                claimer_user_id = $2,
                claimer_username = $3
            WHERE message_id = $1;
            """,
            message_id, user_id, username
        )


async def set_status_canceled(message_id: int, comment: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET status = 'CANCELED',
                cancel_comment = $2
            WHERE message_id = $1;
            """,
            message_id, comment
        )


async def set_status_done(message_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET status = 'DONE',
                archived_at = NOW()
            WHERE message_id = $1;
            """,
            message_id
        )


# -------------------------------------------------------------------------
#  🔁  САМЫЙ ВАЖНЫЙ МЕТОД — “СНОВА В КАНАЛ” (message_id обновляется!)
# -------------------------------------------------------------------------

async def reset_to_pending(old_message_id: int, bot, comment: str) -> Optional[int]:
    """
    🔁 Заявка снова становится “PENDING”.
    👉 ВАЖНО: создаём НОВОЕ сообщение в канале => НОВЫЙ message_id!
    Возвращаем new_message_id (чтобы bot1/другие могли обновить кэш).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        req = await conn.fetchrow("""
            SELECT *
            FROM requests
            WHERE message_id = $1
        """, old_message_id)

    if not req:
        return None  # заявки нет — выходим

    category = req["category"]
    category_h = settings.CATEGORY_H[category]
    channel_id = settings.CATEGORY_TO_CHANNEL[category]

    # 1) Формируем текст заново
    text_back = (
        "🔄 <b>Заявка снова доступна</b>\n\n"
        f"💬 <b>Комментарий специалиста:</b>\n<i>{comment}</i>\n\n"
        f"👤 {req['name']}\n"
        f"⚖️ Категория: {category_h}\n"
        f"🏙 Город: {req['city']}\n"
        f"📝 {req['description']}\n"
        f"🕒 {req['created_at']}"
    )

    # 2) Отправить НОВОЕ сообщение в канал
    new_msg = await bot.send_message(
        chat_id=channel_id,
        text=text_back,
        reply_markup=claim_kb()
    )

    # 3) Обновление записи в БАЗЕ ДАННЫХ
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE requests
            SET message_id = $1,
                status = 'PENDING',
                claimer_user_id = NULL,
                claimer_username = NULL,
                cancel_comment = $3
            WHERE message_id = $2
        """, new_msg.message_id, old_message_id, comment)

    return new_msg.message_id


# -------------------------------------------------------------------------
#  BOT #2 — АРХИВ
# -------------------------------------------------------------------------

async def list_claims_for_user(user_id: int, limit: int = 30):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM requests
            WHERE claimer_user_id = $1 AND status = 'IN_PROGRESS'
            ORDER BY created_at DESC
            LIMIT $2;
            """,
            user_id, limit,
        )
        return [dict(r) for r in rows]
