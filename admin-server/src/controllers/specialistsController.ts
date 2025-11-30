import { Request, Response } from "express";
import {
    createSpecialist,
    deleteSpecialist,
    getAllSpecialists,
    getSpecialistById,
    updateSpecialist
} from "../models/specialistsModel";

export async function getSpecialists(req: Request, res: Response) {
    res.json(await getAllSpecialists());
}

export async function getSpecialist(req: Request, res: Response) {
    const specialist = await getSpecialistById(Number(req.params.id));
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
