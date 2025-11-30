import express from "express";
import dotenv from "dotenv";
import cors from "cors";
import requestsRouter from "./routes/requests";

dotenv.config();
const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// API
app.use("/api/requests", requestsRouter);

app.listen(PORT, () => {
  console.log(`🚀 Admin server running on port ${PORT}`);
});
