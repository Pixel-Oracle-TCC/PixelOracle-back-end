import type { GamePitch } from "../entities/GamePitch.js";
import type { AnalysisResult, RawNarrative } from "../entities/FullReport.js";

export interface IInsightsService {
  /**
   * Redige o resumo e as frases dos destaques a partir do dashboard já montado.
   * A Gemini NÃO analisa do zero — só narra evidências existentes.
   */
  narrateDashboard(pitch: GamePitch, analysis: AnalysisResult): Promise<RawNarrative>;
}
