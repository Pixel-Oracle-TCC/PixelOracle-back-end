import type { Request, Response } from "express";
import type { GetDashboardOverviewUseCase } from "../../application/use-cases/GetDashboardOverviewUseCase.js";
import { parseOptionalGenre } from "../validation/releasesQuery.js";

export class DashboardController {
  constructor(private readonly getDashboardOverview: GetDashboardOverviewUseCase) {}

  async handle(req: Request, res: Response): Promise<Response> {
    const genre = parseOptionalGenre(req.query);
    if (!genre.success) {
      return res.status(400).json({
        status: "erro",
        mensagem: "Gênero inválido.",
        erros: genre.erros,
      });
    }

    try {
      const data = await this.getDashboardOverview.execute(genre.genre);
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
