import "dotenv/config";
import cors from "cors";
import express from "express";

import { GenerateFullReportUseCase } from "./application/use-cases/GenerateFullReportUseCase.js";
import { FallbackInsightsService, GeminiService } from "./services/geminiService.js";
import { MlService } from "./services/mlService.js";
import { errorHandler } from "./presentation/middleware/errorHandler.js";
import { createRoutes } from "./presentation/routes/index.js";

const PORT = Number(process.env.PORT ?? 3000);
const ML_SERVICE_URL = process.env.ML_SERVICE_URL ?? "http://localhost:8000";
const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";
const GEMINI_MODEL = process.env.GEMINI_MODEL ?? "gemini-2.0-flash";

const mlService = new MlService(ML_SERVICE_URL);

const insightsService = GEMINI_API_KEY
  ? new GeminiService(GEMINI_API_KEY, GEMINI_MODEL)
  : new FallbackInsightsService();

if (!GEMINI_API_KEY) {
  console.warn(
    "⚠️  GEMINI_API_KEY não definida — /report usará dicas fallback estáticas."
  );
}

const generateFullReport = new GenerateFullReportUseCase(mlService, insightsService);

const app = express();
app.use(cors());
app.use(express.json());

app.use("/api", createRoutes(generateFullReport, mlService));

app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`🚀 Pixel Oracle BFF — análise de risco e chances de sucesso`);
  console.log(`   http://localhost:${PORT}`);
  console.log(`   ML: ${ML_SERVICE_URL}`);
  console.log(`   Rotas: GET /api/health | POST /api/predict | POST /api/report`);
});
