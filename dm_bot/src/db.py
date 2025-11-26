import asyncpg
from typing import Optional, Dict, Any, List

from .config import settings

_pool: Optional[asyncpg.Pool] = None


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
    Создаёт таблицу заявок, если её нет, и добавляет новые колонки для статусов.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Создать таблицу, если нет
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
                claimer_user_id  BIGINT,
                claimer_username TEXT,
                status           TEXT NOT NULL DEFAULT 'PENDING',
                cancel_comment   TEXT,
                archived_at      TIMESTAMPTZ
            );
            """
        )

        # Добавить новые колонки, если старый формат БД
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PENDING';"
        )
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS cancel_comment TEXT;"
        )
        await conn.execute(
            "ALTER TABLE requests ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;"
        )


# ---------------- BOT #1 ----------------

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
    Сохраняет заявку в БД. Возвращает id записи.
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


async def get_request_by_message_id(message_id: int) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1;",
            message_id,
        )
        return dict(row) if row else None


# СТАРАЯ ФУНКЦИЯ (но оставляем на всякий)
async def set_request_claimed(
    *,
    message_id: int,
    claimer_user_id: int,
    claimer_username: str,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET claimer_user_id  = $2,
                claimer_username = $3,
                status = 'IN_PROGRESS'
            WHERE message_id = $1;
            """,
            message_id,
            claimer_user_id,
            claimer_username,
        )


# ------- НОВЫЕ ФУНКЦИИ СТАТУСОВ (ИСПОЛЬЗУЮТСЯ ВСЕМ ПРОЕКТОМ) -------

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


async def reset_to_pending(message_id: int):
    """
    Возвращает заявку обратно в канал (после отмены).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET status = 'PENDING',
                claimer_user_id = NULL,
                claimer_username = NULL
            WHERE message_id = $1;
            """,
            message_id
        )


async def set_status_done(message_id: int):
    """
    Завершает заявку и отправляет в архив.
    """
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


# ---------------- BOT #2 ----------------

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
            user_id,
            limit,
        )
        return [dict(r) for r in rows]
