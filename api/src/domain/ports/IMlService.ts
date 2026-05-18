import type { GamePitch } from "../entities/GamePitch.js";
import type { MlPredictionResult } from "../entities/MlPrediction.js";

export interface IMlService {
  health(): Promise<Record<string, unknown>>;
  predict(pitch: GamePitch): Promise<MlPredictionResult>;
}
