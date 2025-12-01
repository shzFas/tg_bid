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

ACTIVE_STATUSES = ('CLAIMED', 'RESEND')

async def get_claimed_requests(tg_id: int, page: int, page_size: int):
    conn = await asyncpg.connect(DATABASE_URL)

    # считаем только активные заявки
    total = await conn.fetchval("""
        SELECT COUNT(*) FROM requests 
        WHERE claimed_by_id = $1 AND status = ANY($2::text[])
    """, tg_id, ACTIVE_STATUSES)

    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    rows = await conn.fetch("""
        SELECT * FROM requests
        WHERE claimed_by_id = $1 AND status = ANY($2::text[])
        ORDER BY claimed_at DESC
        LIMIT $3 OFFSET $4
    """, tg_id, ACTIVE_STATUSES, page_size, offset)

    await conn.close()
    return rows, total_pages

async def cancel_request(req_id: int, tg_id: int, note: str | None) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    res = await conn.execute("""
        UPDATE requests SET
            status='CANCELED',
            claimed_by_id=NULL,
            claimed_by_username=NULL,
            claimed_at=NULL,
            cancel_note=$3,
            canceled_at=NOW()
        WHERE id=$1 AND claimed_by_id=$2
    """, req_id, tg_id, note)
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

async def get_request_data(req_id: int) -> dict | None:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT id, phone, name, city, description, specialization,
               tg_chat_id, tg_message_id, sent_by_bot, status,
               claimed_by_id, claimed_at, resend_at, canceled_at
        FROM requests
        WHERE id=$1
    """, req_id)
    await conn.close()
    return dict(row) if row else None

async def save_cancel_note(req_id: int, tg_id: int, note: str | None) -> bool:
    """
    Отмена заявки: сохраняем cancel_note + возвращаем в PENDING.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    res = await conn.execute("""
        UPDATE requests SET
            status='RESEND',
            resend_at=NOW(),
            claimed_by_id=NULL,
            claimed_by_username=NULL,
            claimed_at=NULL,
            cancel_note=$3
        WHERE id=$1 AND claimed_by_id=$2
    """, req_id, tg_id, note)
    await conn.close()
    return res == "UPDATE 1"