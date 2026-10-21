import type { Request, Response } from "express";
import type { GetDashboardOverviewUseCase } from "../../application/use-cases/GetDashboardOverviewUseCase.js";

export class DashboardController {
  constructor(private readonly getDashboardOverview: GetDashboardOverviewUseCase) {}

  async handle(_req: Request, res: Response): Promise<Response> {
    try {
      const data = await this.getDashboardOverview.execute();
      return res.status(200).json({
        status: "sucesso",
        data,
      });
    } catch (error: unknown) {
      console.error(error);
      return res.status(500).json({
        status: "erro",
        mensagem: "Não foi possível carregar o dashboard. Tente novamente mais tarde.",
      });
    }
  }
}
