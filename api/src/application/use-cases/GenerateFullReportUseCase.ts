import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { DashboardNarrative, FullReport } from "../../domain/entities/FullReport.js";
import type { IInsightsService } from "../../domain/ports/IInsightsService.js";
import type { IMlService } from "../../domain/ports/IMlService.js";
import { buildFallbackNarrative } from "../narrative/fallbackNarrative.js";
import { validateNarrative } from "../validation/highlightValidator.js";

/**
 * Relatório completo: o ml-service monta o dashboard de evidências e a Gemini só redige.
 *
 * Ordem importa (decisão de produto/TCC):
 * 1) Evidências estruturadas via /analyze (similares + temas + drivers do RF)
 * 2) Narrativa em português (Gemini ou fallback)
 * 3) Validador: frase que cita jogo fora dos jogos-exemplo volta para o texto-modelo
 *
 * Se a Gemini falhar, NÃO propagamos 500: devolvemos as frases determinísticas.
 * Ver vault: [[Por que Gemini so redige]].
 */
export class GenerateFullReportUseCase {
  constructor(
    private readonly mlService: IMlService,
    private readonly insightsService: IInsightsService,
    private readonly usesGemini: boolean
  ) {}

  async execute(pitch: GamePitch): Promise<FullReport> {
    const analysis = await this.mlService.analyze(pitch);

    let narrativa: DashboardNarrative;
    try {
      const raw = await this.insightsService.narrateDashboard(pitch, analysis);
      narrativa = validateNarrative(analysis, raw, this.usesGemini ? "gemini" : "fallback");
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      console.warn(`[report] Gemini indisponível — usando fallback. Motivo: ${detail}`);
      narrativa = validateNarrative(analysis, buildFallbackNarrative(pitch, analysis), "fallback");
    }

    return {
      status: "sucesso",
      modo: "pre-lancamento",
      jogo: analysis.jogo,
      // Estruturado + evidência (frontend pode renderizar cards sem depender da LLM)
      dashboard: analysis.dashboard,
      narrativa,
      cobertura: analysis.cobertura,
      evidencias: analysis.evidencias,
    };
  }
}
