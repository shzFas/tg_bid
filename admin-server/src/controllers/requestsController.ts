import { Request, Response } from "express";
import {
    getAllRequests,
    getRequestById,
    createRequest,
    updateRequest,
    deleteRequest,
    saveChannelMessage,
    createRequestInChanel,
} from "../models/requestsModel";
import { publishToTelegram } from "../telegram/sender";
import { notifySpecialist } from "../telegram/notify";
import axios from "axios";

function error(res: Response, code: string, message: string, status = 400) {
    return res.status(status).json({
        success: false,
        errorCode: code,
        message
    });
}

function ok(res: Response, data: any) {
    return res.json({
        success: true,
        data,
    });
}

function mapSpecName(spec: string) {
    return spec === "ACCOUNTING" ? "Бухгалтера"
        : spec === "LAW" ? "Адвоката"
            : spec === "EGOV" ? "EGOV"
                : "Специалиста";
}

export async function getRequests(req: Request, res: Response) {
    try {
        const list = await getAllRequests();
        return ok(res, list);
    } catch (err) {
        return error(res, "INTERNAL_ERROR", "Не удалось загрузить список заявок", 500);
    }
}

export async function getRequest(req: Request, res: Response) {
    try {
        const request = await getRequestById(Number(req.params.id));

        if (!request) {
            return error(res, "REQUEST_NOT_FOUND", "Заявка не найдена", 404);
        }

        return ok(res, request);
    } catch (err) {
        return error(res, "INTERNAL_ERROR", "Ошибка загрузки заявки", 500);
    }
}

export async function createNewRequest(req: Request, res: Response) {
    try {
        const newRequest = await createRequest(req.body);
        return ok(res, newRequest);
    } catch (err) {
        return error(res, "CREATE_FAILED", "Не удалось создать заявку", 500);
    }
}

export async function updateExistingRequest(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const updated = await updateRequest(id, req.body);

        if (!updated) {
            return error(res, "REQUEST_NOT_FOUND", "Заявка не найдена", 404);
        }

        return ok(res, updated);

    } catch (err) {
        return error(res, "UPDATE_FAILED", "Ошибка обновления заявки", 500);
    }
}

export async function deleteExistingRequest(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const result = await deleteRequest(id);

        if (!result) {
            return error(res, "REQUEST_NOT_FOUND", "Заявка не найдена", 404);
        }

        return ok(res, { id });

    } catch (err) {
        return error(res, "DELETE_FAILED", "Ошибка удаления заявки", 500);
    }
}

export async function createAndPublish(req: Request, res: Response) {
    try {
        const data = req.body;

        const newRequest = await createRequestInChanel(data);

        const { message_id, chat_id } = await publishToTelegram(newRequest);

        await saveChannelMessage(newRequest.id, message_id, chat_id, "request");

        return ok(res, {
            request_id: newRequest.id,
            tg_message_id: message_id,
            channel_id: chat_id
        });

    } catch (err) {
        return error(res, "CREATE_PUBLISH_FAILED", "Не удалось создать и опубликовать заявку", 500);
    }
}

export async function updateAndRepublish(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const updates = req.body;

        const oldReq = await getRequestById(id);
        if (!oldReq) {
            return error(res, "REQUEST_NOT_FOUND", "Заявка не найдена", 404);
        }

        // ❌ Запрет на редактирование DONE
        if (oldReq.status === "DONE") {
            return error(
                res,
                "EDIT_FORBIDDEN",
                "Нельзя редактировать завершённую заявку (DONE)"
            );
        }

        // ❌ Нельзя менять специализацию если заявка занята
        if (
            oldReq.claimed_by_id &&
            updates.specialization &&
            updates.specialization !== oldReq.specialization
        ) {
            return error(
                res,
                "SPECIALIZATION_LOCKED",
                "Нельзя менять специализацию, пока заявка взята специалистом"
            );
        }

        const updated = await updateRequest(id, updates);

        const botToken = process.env.REQUEST_BOT_TOKEN;
        const oldChat = oldReq.tg_chat_id;
        const oldMsg = oldReq.tg_message_id;

        const newSpec = updated.specialization;
        const oldSpec = oldReq.specialization;

        const newChannelId = process.env[`CHANNEL_${newSpec}_ID`];

        // 📌 Подготовка текста
        let claimedNotice = "";
        let keyboard: any = undefined;

        if (oldReq.claimed_by_id) {
            const uname = oldReq.claimed_by_username || "специалистом";
            claimedNotice = `\n\n👨‍🔧 Заявка уже взята @${uname}`;
        } else {
            keyboard = {
                inline_keyboard: [[{
                    text: "⚒ Взять в работу",
                    callback_data: `claim:${updated.id}`,
                }]]
            };
        }

        const text = `
<b>${mapSpecName(updated.specialization)}</b>

✉ <b>Заявка (ID: ${updated.id})</b>
<b>⚠ Обновлена администратором</b>

👤 <b>Имя:</b> ${updated.name}
🏙 <b>Город:</b> ${updated.city}
📝 <b>Описание:</b> ${updated.description}
${claimedNotice}
        `.trim();

        // 📌 Перенос если specialization изменилась
        if (newSpec !== oldSpec) {
            if (oldChat && oldMsg) {
                await axios.post(
                    `https://api.telegram.org/bot${botToken}/deleteMessage`,
                    { chat_id: oldChat, message_id: oldMsg }
                );
            }

            const resp = await axios.post(
                `https://api.telegram.org/bot${botToken}/sendMessage`,
                {
                    chat_id: newChannelId,
                    text,
                    parse_mode: "HTML",
                    reply_markup: keyboard ?? undefined
                }
            );

            const newMessageId = resp.data.result.message_id;

            await saveChannelMessage(updated.id, newMessageId, newChannelId, "request");

            if (oldReq.claimed_by_id) {
                await notifySpecialist(oldReq.claimed_by_id, updated.id);
            }

            return ok(res, { moved: true });
        }

        // 📌 Просто редактируем
        if (oldChat && oldMsg) {
            await axios.post(
                `https://api.telegram.org/bot${botToken}/editMessageText`,
                {
                    chat_id: oldChat,
                    message_id: oldMsg,
                    text,
                    parse_mode: "HTML",
                    reply_markup: keyboard ?? undefined
                }
            );
        }

        if (oldReq.claimed_by_id) {
            await notifySpecialist(oldReq.claimed_by_id, updated.id);
        }

        return ok(res, { edited: true, updated });

    } catch (err) {
        console.error(err);
        return error(res, "UPDATE_PUBLISH_FAILED", "Не удалось обновить и перепубликовать заявку", 500);
    }
}
