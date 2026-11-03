import { Router } from "express";
import { GetDashboardOverviewUseCase } from "../../application/use-cases/GetDashboardOverviewUseCase.js";
import { GetReleasesUseCase } from "../../application/use-cases/GetReleasesUseCase.js";
import type { IMlService } from "../../domain/ports/IMlService.js";
import { pool } from "../../infrastructure/database/pool.js";
import { PgDashboardRepository } from "../../infrastructure/repositories/PgDashboardRepository.js";
import { CorrelationHeatmapController } from "../controllers/correlationHeatmapController.js";
import { DashboardController } from "../controllers/dashboardController.js";
import { ReleasesController } from "../controllers/releasesController.js";

const repository = new PgDashboardRepository(pool);
const getDashboardOverview = new GetDashboardOverviewUseCase(repository);
const getReleases = new GetReleasesUseCase(repository);

const dashboardController = new DashboardController(getDashboardOverview);
const releasesController = new ReleasesController(getReleases);

export function createDashboardRoutes(mlService: IMlService): Router {
  const correlationHeatmapController = new CorrelationHeatmapController(mlService);
  const router = Router();

  router.get("/dashboard", (req, res) => dashboardController.handle(req, res));
  router.get("/releases", (req, res) => releasesController.handle(req, res));
  router.get("/correlation-heatmap", (req, res, next) =>
    correlationHeatmapController.handle(req, res, next)
  );

  return router;
}
