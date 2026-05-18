import type { GamePitch } from "../entities/GamePitch.js";
import type { MlPredictionResult } from "../entities/MlPrediction.js";
import type { CommercialInsights } from "../entities/FullReport.js";

export interface IInsightsService {
  generateCommercialTips(
    pitch: GamePitch,
    prediction: MlPredictionResult
  ): Promise<CommercialInsights>;
}
