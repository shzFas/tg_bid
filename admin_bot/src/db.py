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
    Создаём все таблицы (requests + specialists + categories).
    Безопасно вызывать при старте любого бота.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Старая таблица из bot/dm_bot
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

        # Список специалистов
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS specialists (
                id BIGSERIAL PRIMARY KEY,
                tg_user_id  BIGINT UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        # Связь специалиста с категориями ('ACCOUNTING', 'LAW', 'EGOV')
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS specialist_categories (
                id BIGSERIAL PRIMARY KEY,
                specialist_id BIGINT NOT NULL REFERENCES specialists(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                UNIQUE(specialist_id, category)
            );
            """
        )


# -----------------------
# FUNCTIONS: specialists
# -----------------------

async def get_or_create_specialist(
    tg_user_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> Dict[str, Any]:
    """
    Создаёт специалиста, если его нет, иначе обновляет username/full_name.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO specialists (tg_user_id, username, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (tg_user_id) DO UPDATE
            SET username = EXCLUDED.username,
                full_name = EXCLUDED.full_name
            RETURNING *;
            """,
            tg_user_id,
            username,
            full_name,
        )
        return dict(row)


async def set_specialist_categories(tg_user_id: int, categories: list[str]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        spec = await conn.fetchrow("SELECT id FROM specialists WHERE tg_user_id = $1", tg_user_id)
        if not spec:
            raise ValueError("Сначала нужно вызвать /add_spec!")

        spec_id = spec["id"]
        await conn.execute("DELETE FROM specialist_categories WHERE specialist_id = $1", spec_id)

        for cat in categories:  # cat: ACCOUNTING/Law/egov...
            await conn.execute(
                """
                INSERT INTO specialist_categories (specialist_id, category)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                spec_id,
                cat,
            )


async def get_specialists_list() -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.tg_user_id, s.username, s.is_active,
                   array_agg(sc.category) AS categories
            FROM specialists s
            LEFT JOIN specialist_categories sc ON sc.specialist_id = s.id
            GROUP BY s.id
            ORDER BY s.id;
            """
        )
        return [dict(r) for r in rows]


async def is_specialist_allowed(tg_user_id: int, category: str) -> bool:
    """
    Проверить, может ли данный user брать заявку этой категории.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT sc.category
            FROM specialists s
            JOIN specialist_categories sc ON sc.specialist_id = s.id
            WHERE s.tg_user_id = $1
              AND s.is_active = TRUE
              AND sc.category = $2
            """,
            tg_user_id,
            category,
        )
        return bool(row)


