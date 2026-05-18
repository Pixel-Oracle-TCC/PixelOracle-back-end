import { Router } from "express";
import type { GenerateFullReportUseCase } from "../../application/use-cases/GenerateFullReportUseCase.js";
import type { IMlService } from "../../domain/ports/IMlService.js";
import { createReportController } from "../controllers/reportController.js";

export function createRoutes(
  generateReport: GenerateFullReportUseCase,
  mlService: IMlService
): Router {
  const router = Router();
  const controller = createReportController(generateReport, mlService);

  router.get("/health", controller.health);
  router.post("/predict", controller.predictOnly);
  router.post("/report", controller.fullReport);

  return router;
}
