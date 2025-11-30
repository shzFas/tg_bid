import { pool } from "../db";

export async function getAllSpecialists() {
    const { rows } = await pool.query("SELECT * FROM specialists ORDER BY id DESC");
    return rows;
}

export async function getSpecialistById(id: number) {
    const { rows } = await pool.query("SELECT * FROM specialists WHERE id = $1", [id]);
    return rows[0];
}

export async function createSpecialist(data: any) {
    const { tg_id, username, name, phone, is_approved, specializations } = data;

    const { rows } = await pool.query(
        `INSERT INTO specialists (tg_id, username, name, phone, is_approved, specializations)
     VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
        [tg_id, username, name, phone, is_approved ?? false, specializations]
    );
    return rows[0];
}

export async function updateSpecialist(id: number, data: any) {
    const { tg_id, username, name, phone, is_approved, specializations } = data;

    const { rows } = await pool.query(
        `UPDATE specialists
     SET tg_id=$1, username=$2, name=$3, phone=$4, is_approved=$5, specializations=$6
     WHERE id = $7 RETURNING *`,
        [tg_id, username, name, phone, is_approved, specializations, id]
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
