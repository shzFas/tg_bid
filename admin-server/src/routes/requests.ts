import { Router } from "express";
import {
    getRequests,
    getRequest,
    createNewRequest,
    updateExistingRequest,
    deleteExistingRequest,
    createAndPublish,
    updateAndRepublish
} from "../controllers/requestsController";

const router = Router();

router.get("/", getRequests);
router.get("/:id", getRequest);
router.post("/", createNewRequest);
router.put("/:id", updateExistingRequest);

router.delete("/:id", deleteExistingRequest);
router.post("/create-and-publish", createAndPublish);
router.put("/:id/publish-update", updateAndRepublish);

export default router;
