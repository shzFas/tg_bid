import { pool } from "../db";

function normalizeSpecs(value: any) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    return value.split(",").map(s => s.trim());
  }
  return [];
}

export async function getAllSpecialists() {
  const { rows } = await pool.query("SELECT * FROM specialists ORDER BY id DESC");
  return rows;
}

export async function getSpecialistById(id: number) {
  const { rows } = await pool.query("SELECT * FROM specialists WHERE id = $1", [id]);
  return rows[0];
}

export async function createSpecialist(data: any) {
  const { tg_id, username, name, phone, is_approved } = data;
  const specs = normalizeSpecs(data.specializations);

  const { rows } = await pool.query(
    `INSERT INTO specialists (tg_id, username, name, phone, is_approved, specializations)
     VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
    [tg_id || null, username || null, name, phone, is_approved ?? false, specs]
  );
  return rows[0];
}

export async function updateSpecialist(id: number, data: any) {
  const { tg_id, username, name, phone, is_approved } = data;
  const specs = normalizeSpecs(data.specializations);

  const { rows } = await pool.query(
    `UPDATE specialists
     SET tg_id=$1, username=$2, name=$3, phone=$4, is_approved=$5, specializations=$6
     WHERE id = $7 RETURNING *`,
    [tg_id || null, username || null, name, phone, is_approved, specs, id]
  );
  return rows[0];
}

export async function deleteSpecialist(id: number) {
  const { rows } = await pool.query(
    `DELETE FROM specialists WHERE id = $1 RETURNING *`,
    [id]
  );
  return rows[0];
}

export async function approveSpecialist(id: number) {
  await pool.query(
    `UPDATE specialists 
     SET is_approved=true
     WHERE id=$1`,
    [id]
  );
}
