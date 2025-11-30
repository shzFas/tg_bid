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
