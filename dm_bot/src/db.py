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
    Создает таблицу заявок, если её ещё нет.
    Эту функцию можно безопасно вызывать из обоих ботов.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
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
                claimer_username TEXT
            );
            """
        )


# ---------- функции для bot #1 ----------

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
                message_id,
                category,
                name,
                phone,
                city,
                description
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
        return int(row["id"])


async def get_request_by_message_id(message_id: int) -> Optional[Dict[str, Any]]:
    """
    Возвращает заявку по message_id (сообщение в канале).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM requests WHERE message_id = $1;",
            message_id,
        )
        return dict(row) if row else None


async def set_request_claimed(
    *,
    message_id: int,
    claimer_user_id: int,
    claimer_username: str,
) -> None:
    """
    Обновляет заявку, помечая её как принятую определённым пользователем.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE requests
            SET claimer_user_id  = $2,
                claimer_username = $3
            WHERE message_id = $1;
            """,
            message_id,
            claimer_user_id,
            claimer_username,
        )


async def list_requests(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Список всех заявок (для будущего экспорта в Excel, CRM и т.п.)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM requests
            ORDER BY created_at DESC
            LIMIT $1;
            """,
            limit,
        )
        return [dict(r) for r in rows]


# ---------- функции для dm_bot (#2) ----------

async def list_claims_for_user(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Список заявок, которые принял данный пользователь (для /my, /tasks).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM requests
            WHERE claimer_user_id = $1
            ORDER BY created_at DESC
            LIMIT $2;
            """,
            user_id,
            limit,
        )
        return [dict(r) for r in rows]
