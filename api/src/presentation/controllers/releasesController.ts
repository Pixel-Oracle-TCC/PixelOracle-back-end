import type { Request, Response } from "express";
import type { GetReleasesUseCase } from "../../application/use-cases/GetReleasesUseCase.js";
import { parseOptionalGenre, parseReleasesQuery } from "../validation/releasesQuery.js";

export class ReleasesController {
  constructor(private readonly getReleases: GetReleasesUseCase) {}

  async handle(req: Request, res: Response): Promise<Response> {
    const parsed = parseReleasesQuery(req.query);
    const genre = parseOptionalGenre(req.query);
    if (!parsed.success || !genre.success) {
      return res.status(400).json({
        status: "erro",
        mensagem: "Parâmetros de data inválidos.",
        erros: [...(parsed.success ? [] : parsed.erros), ...(genre.success ? [] : genre.erros)],
      });
    }

    try {
      const data = await this.getReleases.execute(parsed.data.from, parsed.data.to, genre.genre);
      return res.status(200).json({
        status: "sucesso",
        data,
      });
    } catch (error: unknown) {
      console.error(error);
      return res.status(500).json({
        status: "erro",
        mensagem: "Não foi possível carregar os lançamentos. Tente novamente mais tarde.",
      });
    }
  }
}
