import type { GamePitch } from "../entities/GamePitch.js";
import type { MlPredictionResult } from "../entities/MlPrediction.js";
import type { TriangulationResult } from "../entities/FullReport.js";

export interface IMlService {
  health(): Promise<Record<string, unknown>>;
  predict(pitch: GamePitch): Promise<MlPredictionResult>;
  triangulate(pitch: GamePitch): Promise<TriangulationResult>;
}
