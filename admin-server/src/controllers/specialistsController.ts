import { Request, Response } from "express";
import {
    approveSpecialist,
    createSpecialist,
    deleteSpecialist,
    getAllSpecialists,
    getSpecialistById,
    updateSpecialist
} from "../models/specialistsModel";
import { sendApproveTelegram } from "../telegram/notify";

function normalizeSpecArray(specialist: any) {
  if (Array.isArray(specialist.specializations)) return specialist;
  if (typeof specialist.specializations === "string") {
    specialist.specializations = specialist.specializations
      .split(",")
      .map((s: string) => s.trim());
  }
  return specialist;
}

export async function getSpecialists(req: Request, res: Response) {
  let specialists = await getAllSpecialists();
  specialists = specialists.map(normalizeSpecArray);
  res.json(specialists);
}

export async function getSpecialist(req: Request, res: Response) {
  let specialist = await getSpecialistById(Number(req.params.id));
  specialist = normalizeSpecArray(specialist);
  specialist ? res.json(specialist) : res.status(404).json({ error: "Not found" });
}

export async function createNewSpecialist(req: Request, res: Response) {
    try {
        const newSpecialist = await createSpecialist(req.body);
        return res.status(201).json(newSpecialist);
    } catch (error) {
        return res.status(500).json({ error: "Failed to create specialist", details: error });
    }
}

export async function updateExistingSpecialist(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const updated = await updateSpecialist(id, req.body);
        updated
            ? res.json(updated)
            : res.status(404).json({ error: "Specialist not found" });
    } catch (error) {
        res.status(500).json({ error: "Failed to update specialist", details: error });
    }
}

export async function deleteExistingSpecialist(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const result = await deleteSpecialist(id);

        result
            ? res.json(result)
            : res.status(404).json({ error: "Specialist not found" });

    } catch (error) {
        res.status(500).json({ error: "Failed to delete specialist", details: error });
    }
}

export async function approveSpecialistRoute(req: Request, res: Response) {
  try {
    const id = Number(req.params.id);

    const specialist = await getSpecialistById(id);
    if (!specialist) return res.status(404).json({ error: "Not found" });

    // 1) Обновляем статус
    await approveSpecialist(id);

    // 2) Уведомляем в Telegram
    await sendApproveTelegram(specialist);

    return res.json({ success: true });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Failed to approve specialist" });
  }
}
