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

/* Унифицированные ответы */
function error(res: Response, code: string, message: string, status = 400) {
  return res.status(status).json({
    success: false,
    errorCode: code,
    message,
  });
}

function ok(res: Response, data: any) {
  return res.json({
    success: true,
    data,
  });
}

/* Приведение специализаций к массиву */
function normalizeSpecArray(specialist: any) {
  if (!specialist) return null;

  if (Array.isArray(specialist.specializations)) return specialist;

  if (typeof specialist.specializations === "string") {
    specialist.specializations = specialist.specializations
      .split(",")
      .map((s: string) => s.trim());
  }

  return specialist;
}

/* ===================== */
/*      ROUTES           */
/* ===================== */

export async function getSpecialists(req: Request, res: Response) {
  try {
    let specialists = await getAllSpecialists();
    specialists = specialists.map(normalizeSpecArray);
    return ok(res, specialists);
  } catch (err) {
    return error(res, "INTERNAL_ERROR", "Не удалось загрузить специалистов", 500);
  }
}

export async function getSpecialist(req: Request, res: Response) {
  try {
    let specialist = await getSpecialistById(Number(req.params.id));

    if (!specialist) {
      return error(res, "SPECIALIST_NOT_FOUND", "Специалист не найден", 404);
    }

    specialist = normalizeSpecArray(specialist);
    return ok(res, specialist);

  } catch (err) {
    return error(res, "INTERNAL_ERROR", "Ошибка получения специалиста", 500);
  }
}

export async function createNewSpecialist(req: Request, res: Response) {
  try {
    const newSpecialist = await createSpecialist(req.body);
    return ok(res, newSpecialist);
  } catch (err) {
    return error(res, "CREATE_FAILED", "Не удалось создать специалиста", 500);
  }
}

export async function updateExistingSpecialist(req: Request, res: Response) {
  try {
    const id = Number(req.params.id);
    const updated = await updateSpecialist(id, req.body);

    if (!updated) {
      return error(res, "SPECIALIST_NOT_FOUND", "Специалист не найден", 404);
    }

    return ok(res, updated);

  } catch (err) {
    return error(res, "UPDATE_FAILED", "Не удалось обновить специалиста", 500);
  }
}

export async function deleteExistingSpecialist(req: Request, res: Response) {
  try {
    const id = Number(req.params.id);
    const result = await deleteSpecialist(id);

    if (!result) {
      return error(res, "SPECIALIST_NOT_FOUND", "Специалист не найден", 404);
    }

    return ok(res, { id });

  } catch (err) {
    return error(res, "DELETE_FAILED", "Не удалось удалить специалиста", 500);
  }
}

export async function approveSpecialistRoute(req: Request, res: Response) {
  try {
    const id = Number(req.params.id);
    const specialist = await getSpecialistById(id);

    if (!specialist) {
      return error(res, "SPECIALIST_NOT_FOUND", "Специалист не найден", 404);
    }

    // 1) обновляем статус
    await approveSpecialist(id);

    // 2) отправляем уведомление
    await sendApproveTelegram(specialist);

    return ok(res, { approved: true });

  } catch (err) {
    console.error(err);
    return error(res, "APPROVE_FAILED", "Не удалось утвердить специалиста", 500);
  }
}
