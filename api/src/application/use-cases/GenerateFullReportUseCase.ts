import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { FullReport } from "../../domain/entities/FullReport.js";
import type { IInsightsService } from "../../domain/ports/IInsightsService.js";
import type { IMlService } from "../../domain/ports/IMlService.js";

export class GenerateFullReportUseCase {
  constructor(
    private readonly mlService: IMlService,
    private readonly insightsService: IInsightsService
  ) {}

  async execute(pitch: GamePitch): Promise<FullReport> {
    const predicao_ml = await this.mlService.predict(pitch);
    const insights = await this.insightsService.generateCommercialTips(
      pitch,
      predicao_ml
    );

    return {
      status: "sucesso",
      modo: "pre-lancamento",
      jogo: {
        titulo: pitch.titulo,
        descricao: pitch.descricao,
      },
      predicao_ml,
      insights,
    };
  }
}
