import type { GamePitch } from "../entities/GamePitch.js";
import type { AnalysisResult } from "../entities/FullReport.js";

export interface IMlService {
  health(): Promise<Record<string, unknown>>;
  analyze(pitch: GamePitch): Promise<AnalysisResult>;
}
