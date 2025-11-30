import { pool } from "../db";

export async function getAllRequests() {
  const res = await pool.query("SELECT * FROM requests ORDER BY created_at DESC");
  return res.rows;
}

export async function getRequestById(id: number) {
  const res = await pool.query("SELECT * FROM requests WHERE id = $1", [id]);
  return res.rows[0];
}

export async function createRequest(data: any) {
  const query = `
    INSERT INTO requests (phone, name, city, description, specialization, tg_chat_id)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING *;
  `;
  const values = [
    data.phone,
    data.name,
    data.city,
    data.description,
    data.specialization,
    data.tg_chat_id || null,
  ];
  const res = await pool.query(query, values);
  return res.rows[0];
}

export async function updateRequest(id: number, data: any) {
  // 1. получаем текущую запись
  const current = await pool.query("SELECT * FROM requests WHERE id = $1", [id]);
  if (!current.rows[0]) return null;

  const request = { ...current.rows[0], ...data }; // merge

  // 2. SQL обновление всех полей
  const query = `
    UPDATE requests SET
      phone = $1,
      name = $2,
      city = $3,
      description = $4,
      specialization = $5,
      status = $6,
      claimed_by_id = $7,
      claimed_by_username = $8,
      claimed_at = $9
    WHERE id = $10
    RETURNING *;
  `;

  const values = [
    request.phone,
    request.name,
    request.city,
    request.description,
    request.specialization,
    request.status,
    request.claimed_by_id,
    request.claimed_by_username,
    request.claimed_at,
    id,
  ];

  const res = await pool.query(query, values);
  return res.rows[0];
}

export async function deleteRequest(id: number) {
  const res = await pool.query("DELETE FROM requests WHERE id = $1 RETURNING id", [id]);
  return res.rowCount > 0
    ? { message: "Request deleted" }
    : null;
}

