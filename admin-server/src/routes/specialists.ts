import { Router } from "express";
import {
    approveSpecialistRoute,
    createNewSpecialist,
    deleteExistingSpecialist,
    getSpecialist,
    getSpecialists,
    updateExistingSpecialist
} from "../controllers/specialistsController";

const router = Router();

router.get("/", getSpecialists);
router.get("/:id", getSpecialist);
router.post("/", createNewSpecialist);
router.put("/:id", updateExistingSpecialist);
router.delete("/:id", deleteExistingSpecialist);

router.post("/:id/approve", approveSpecialistRoute);

export default router;
