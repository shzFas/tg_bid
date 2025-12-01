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

export async function getRequests(req: Request, res: Response) {
    res.json(await getAllRequests());
}

export async function getRequest(req: Request, res: Response) {
    const request = await getRequestById(Number(req.params.id));
    request ? res.json(request) : res.status(404).json({ error: "Not found" });
}

export async function createNewRequest(req: Request, res: Response) {
    try {
        const newRequest = await createRequest(req.body);
        return res.status(201).json(newRequest);
    } catch (error) {
        return res.status(500).json({ error: "Failed to create request", details: error });
    }
}

export async function updateExistingRequest(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const updated = await updateRequest(id, req.body);
        updated
            ? res.json(updated)
            : res.status(404).json({ error: "Request not found" });
    } catch (error) {
        res.status(500).json({ error: "Failed to update request", details: error });
    }
}

export async function deleteExistingRequest(req: Request, res: Response) {
    try {
        const id = Number(req.params.id);
        const result = await deleteRequest(id);

        result
            ? res.json(result)
            : res.status(404).json({ error: "Request not found" });

    } catch (error) {
        res.status(500).json({ error: "Failed to delete request", details: error });
    }
}

export async function createAndPublish(req: Request, res: Response) {
  try {
    const data = req.body;

    const newRequest = await createRequestInChanel(data);

    const { message_id, chat_id } = await publishToTelegram(newRequest);

    await saveChannelMessage(newRequest.id, message_id, chat_id, "request");

    return res.status(201).json({
      success: true,
      request_id: newRequest.id,
      tg_message_id: message_id,
      channel_id: chat_id,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Failed to create & publish" });
  }
}
