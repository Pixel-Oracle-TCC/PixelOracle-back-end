import type { GamePitch } from "../entities/GamePitch.js";
import type {
  DashboardNarrative,
  TriangulationResult,
} from "../entities/FullReport.js";

export interface IInsightsService {
  /**
   * Redige o dashboard a partir do objeto já triangulado.
   * A Gemini NÃO analisa do zero — só narra evidências existentes.
   */
  narrateDashboard(
    pitch: GamePitch,
    triangulation: TriangulationResult
  ): Promise<DashboardNarrative>;
}
