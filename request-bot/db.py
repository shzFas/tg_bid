import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def save_request(data: dict):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO requests (phone, name, city, description, specialization, tg_chat_id, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'PENDING')
    """, data["phone"], data["name"], data["city"], data["description"], data["specialization"], data["tg_chat_id"])
    await conn.close()
