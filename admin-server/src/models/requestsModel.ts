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
    const fields = [];
    const values: any[] = [];

    Object.entries(data).forEach(([key, value], index) => {
        fields.push(`${key} = $${index + 1}`);
        values.push(value);
    });

    if (fields.length === 0) return null;

    const query = `
    UPDATE requests
    SET ${fields.join(", ")}
    WHERE id = $${fields.length + 1}
    RETURNING *;
  `;

    values.push(id);
    const res = await pool.query(query, values);
    return res.rows[0];
}

export async function deleteRequest(id: number) {
    const res = await pool.query("DELETE FROM requests WHERE id = $1 RETURNING id", [id]);
    return res.rowCount > 0 ? { message: "Request deleted" } : null;
}
