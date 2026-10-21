/**
 * Bootstrap da API principal (porta pública do frontend).
 *
 * DI manual (sem Nest): monta MlService + Gemini/Fallback → GenerateFullReportUseCase
 * e o pool Postgres → repositório de KPIs.
 * Ver vault: [[Por que dois servicos e um banco]] / [[Por que Ports and Adapters]].
 */
import "dotenv/config";
import cors from "cors";
import express from "express";

import { GenerateFullReportUseCase } from "./application/use-cases/GenerateFullReportUseCase.js";
import { FallbackInsightsService, GeminiService } from "./services/geminiService.js";
import { MlService } from "./services/mlService.js";
import { errorHandler } from "./presentation/middleware/errorHandler.js";
import { dashboardRoutes } from "./presentation/routes/dashboard.routes.js";
import { createRoutes } from "./presentation/routes/index.js";

const PORT = Number(process.env.PORT ?? 3000);
const ML_SERVICE_URL = process.env.ML_SERVICE_URL ?? "http://localhost:8000";
const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";
const GEMINI_MODEL = process.env.GEMINI_MODEL ?? "gemini-2.5-flash";

const mlService = new MlService(ML_SERVICE_URL);

// Sem chave: produto ainda funciona (narrativa fallback a partir do dashboard)
const insightsService = GEMINI_API_KEY
  ? new GeminiService(GEMINI_API_KEY, GEMINI_MODEL)
  : new FallbackInsightsService();

if (!GEMINI_API_KEY) {
  console.warn(
    "⚠️  GEMINI_API_KEY não definida — /report usará as frases determinísticas do ml-service."
  );
}

if (!process.env.DATABASE_URL) {
  console.warn(
    "⚠️  DATABASE_URL não definida — GET /kpis/dashboard e /kpis/releases falharão ao consultar o Postgres."
  );
}

const generateFullReport = new GenerateFullReportUseCase(
  mlService,
  insightsService,
  Boolean(GEMINI_API_KEY)
);

const app = express();
app.use(cors());
app.use(express.json());

app.use("/api", createRoutes(generateFullReport, mlService));
app.use("/kpis", dashboardRoutes);

app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`🚀 Pixel Oracle — API principal (dashboard de evidências de reviews)`);
  console.log(`   http://localhost:${PORT}`);
  console.log(`   ML: ${ML_SERVICE_URL}`);
  console.log(`   Rotas: GET /api/health | POST /api/report | GET /kpis/dashboard | GET /kpis/releases`);
});
