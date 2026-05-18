import type { Request, Response, NextFunction } from "express";
import type { GenerateFullReportUseCase } from "../../application/use-cases/GenerateFullReportUseCase.js";
import type { IMlService } from "../../domain/ports/IMlService.js";
import { parseGamePitch } from "../validation/parseGamePitch.js";

export function createReportController(
  generateReport: GenerateFullReportUseCase,
  mlService: IMlService
) {
  return {
    async health(_req: Request, res: Response, next: NextFunction) {
      try {
        const ml = await mlService.health();
        res.json({
          status: "online",
          bff: "pixel-oracle-api",
          modo: "pre-lancamento",
          ml_service: ml,
        });
      } catch (err) {
        next(err);
      }
    },

    async predictOnly(req: Request, res: Response, next: NextFunction) {
      try {
        const pitch = parseGamePitch(req.body);
        const result = await mlService.predict(pitch);
        res.json(result);
      } catch (err) {
        next(err);
      }
    },

    async fullReport(req: Request, res: Response, next: NextFunction) {
      try {
        const pitch = parseGamePitch(req.body);
        const report = await generateReport.execute(pitch);
        res.json(report);
      } catch (err) {
        next(err);
      }
    },
  };
}
