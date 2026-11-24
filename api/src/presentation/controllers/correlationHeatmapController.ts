import type { Request, Response, NextFunction } from "express";
import type { IMlService } from "../../domain/ports/IMlService.js";

export class CorrelationHeatmapController {
  constructor(private readonly mlService: IMlService) {}

  async handle(_req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const png = await this.mlService.correlationHeatmap();
      res.setHeader("Content-Type", "image/png");
      res.setHeader("Cache-Control", "no-store");
      res.status(200).send(png);
    } catch (err) {
      next(err);
    }
  }
}
