import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { FullReport } from "../../domain/entities/FullReport.js";
import type { IInsightsService } from "../../domain/ports/IInsightsService.js";
import type { IMlService } from "../../domain/ports/IMlService.js";

/**
 * Relatório completo: triangula no ml-service e pede à Gemini apenas a redação.
 *
 * Ordem importa (decisão de produto/TCC):
 * 1) Evidências estruturadas via /triangulate (RF + RAG + genre_insights)
 * 2) Narrativa em português (Gemini ou fallback)
 *
 * Se a Gemini falhar, NÃO propagamos 500: devolvemos o dashboard bruto.
 * Ver vault: [[Por que Gemini so redige]].
 */
export class GenerateFullReportUseCase {
  constructor(
    private readonly mlService: IMlService,
    private readonly insightsService: IInsightsService
  ) {}

  async execute(pitch: GamePitch): Promise<FullReport> {
    // Análise fundamentada — acontece no ml-service, não no prompt
    const triangulation = await this.mlService.triangulate(pitch);

    let narrativa;
    try {
      narrativa = await this.insightsService.narrateDashboard(pitch, triangulation);
    } catch (err) {
      // Critério de aceite: fallback funcional se Gemini cair (rede, quota, parse)
      const detail = err instanceof Error ? err.message : String(err);
      console.warn(`[report] Gemini indisponível — usando fallback. Motivo: ${detail}`);
      narrativa = {
        resumo:
          "Narrativa Gemini indisponível — exibindo dashboard triangulado bruto.",
        pontos_fortes: triangulation.dashboard.pontos_fortes.map((p) => p.ponto),
        pontos_fracos: triangulation.dashboard.pontos_fracos.map((p) => p.ponto),
        oportunidades: triangulation.dashboard.oportunidades.map((p) => p.ponto),
        riscos: triangulation.dashboard.riscos.map((p) => p.ponto),
        fonte: "fallback" as const,
      };
    }

    return {
      status: "sucesso",
      modo: "pre-lancamento",
      jogo: {
        titulo: pitch.titulo,
        descricao: pitch.descricao,
      },
      predicao_ml: triangulation.predicao_ml,
      // Estruturado + evidência (frontend pode renderizar cards sem depender da LLM)
      dashboard: triangulation.dashboard,
      narrativa,
      evidencias: triangulation.evidencias,
      aviso: triangulation.aviso,
    };
  }
}
