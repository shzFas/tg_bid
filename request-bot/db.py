import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ---------------------------
#  Сохранение заявки + ID
# ---------------------------
async def save_request(data: dict) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        INSERT INTO requests (phone, name, city, description, specialization, status)
        VALUES ($1, $2, $3, $4, $5, 'PENDING')
        RETURNING id
    """, data["phone"], data["name"], data["city"], data["desc"], data["category"])
    await conn.close()
    return row["id"]


# ---------------------------
#  Сохранить message_id + chat_id
# ---------------------------
async def save_message_id(req_id: int, message_id: int, channel_id: str):
    conn = await asyncpg.connect(DATABASE_URL)

    await conn.execute("""
        UPDATE requests
        SET tg_message_id=$1, tg_chat_id=$2
        WHERE id=$3
    """, str(message_id), str(channel_id), req_id)   # <-- FIX HERE!

    await conn.close()


# ---------------------------
#  CLAIM — взято в работу
# ---------------------------
async def set_claimed(req_id: int, tg_id: int, username: str):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        UPDATE requests
        SET claimed_by_id=$1,
            claimed_by_username=$2,
            status='CLAIMED',
            claimed_at=NOW()
        WHERE id=$3
    """, tg_id, username, req_id)
    await conn.close()


# ---------------------------
#  Проверка — взяли ли уже
# ---------------------------
async def request_already_claimed(req_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT status FROM requests WHERE id=$1", req_id)
    await conn.close()
    return row and row["status"] == "CLAIMED"


# ---------------------------
#  Получить данные заявки
# ---------------------------
async def get_request_data(req_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT id, phone, name, city, description, specialization,
               tg_chat_id, tg_message_id
        FROM requests
        WHERE id=$1
    """, req_id)
    await conn.close()
    return dict(row) if row else None


# ============================================================
#   ДОПОЛНИТЕЛЬНЫЙ ФУНКЦИОНАЛ (для Spec-Bot)
# ============================================================

# Проверка — одобрен ли специалист
async def check_approved_specialist(tg_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT is_approved FROM specialists
        WHERE tg_id = $1
    """, tg_id)
    await conn.close()
    return bool(row and row["is_approved"])


# Получить ID специалиста (для связки в других запросах)
async def get_specialist_id(tg_id: int) -> int | None:
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT id FROM specialists
        WHERE tg_id = $1
    """, tg_id)
    await conn.close()
    return row["id"] if row else None


# Показать все заявки, которые специалист взял
async def get_claimed_requests(tg_id: int, page: int, page_size: int):
    conn = await asyncpg.connect(DATABASE_URL)

    total = await conn.fetchval("""
        SELECT COUNT(*) FROM requests
        WHERE claimed_by_id = $1
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


# Вернуть заявку в PENDING (отмена)
async def cancel_request(req_id: int, tg_id: int) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    res = await conn.execute("""
        UPDATE requests
        SET status = 'PENDING',
            claimed_by_id = NULL,
            claimed_by_username = NULL,
            claimed_at = NULL
        WHERE id = $1 AND claimed_by_id = $2
    """, req_id, tg_id)
    await conn.close()
    return res == "UPDATE 1"
