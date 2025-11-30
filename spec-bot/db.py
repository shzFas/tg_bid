import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def specialist_exists(tg_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT 1 FROM specialists WHERE tg_id=$1", tg_id)
    await conn.close()
    return bool(row)

async def save_specialist(tg_id: int, username: str, data: dict):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO specialists (tg_id, username, name, phone, specializations)
        VALUES ($1, $2, $3, $4, $5)
    """, tg_id, username, data["name"], data["phone"], data["specialization"])
    await conn.close()

async def is_approved_specialist(tg_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT is_approved FROM specialists WHERE tg_id=$1", tg_id)
    await conn.close()
    return bool(row and row["is_approved"])


async def get_specialist_id(tg_id: int) -> int | None:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT id FROM specialists WHERE tg_id=$1", tg_id)
    await conn.close()
    return row["id"] if row else None


async def get_claimed_requests(tg_id: int, page: int, page_size: int):
    conn = await asyncpg.connect(DATABASE_URL)

    total = await conn.fetchval("""
        SELECT COUNT(*) FROM requests WHERE claimed_by_id = $1
    """, tg_id)
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size

    rows = await conn.fetch("""
        SELECT * FROM requests
        WHERE claimed_by_id = $1
        ORDER BY claimed_at DESC
        LIMIT $2 OFFSET $3
    """, tg_id, page_size, offset)

    await conn.close()
    return rows, total_pages

async def cancel_request(req_id: int, tg_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    res = await conn.execute("""
        UPDATE requests SET
            status='PENDING',
            claimed_by_id=NULL,
            claimed_by_username=NULL,
            claimed_at=NULL
        WHERE id=$1 AND claimed_by_id=$2
    """, req_id, tg_id)
    await conn.close()
    return res == "UPDATE 1"


async def complete_request(req_id: int, tg_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    res = await conn.execute("""
        UPDATE requests SET
            status='DONE',
            finished_at=NOW()
        WHERE id=$1 AND claimed_by_id=$2
    """, req_id, tg_id)
    await conn.close()
    return res == "UPDATE 1"


