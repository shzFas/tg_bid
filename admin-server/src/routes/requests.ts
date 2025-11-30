import { Router } from "express";
import {
  getRequests,
  getRequest,
  createNewRequest,
  updateExistingRequest,
  deleteExistingRequest
} from "../controllers/requestsController";

const router = Router();

router.get("/", getRequests);
router.get("/:id", getRequest);
router.post("/", createNewRequest);
router.put("/:id", updateExistingRequest);
router.delete("/:id", deleteExistingRequest);

export default router;
