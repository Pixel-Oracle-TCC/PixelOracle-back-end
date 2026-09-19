import axios, { type AxiosInstance } from "axios";
import type { GamePitch } from "../domain/entities/GamePitch.js";
import type { IMlService } from "../domain/ports/IMlService.js";
import type { MlPredictionResult } from "../domain/entities/MlPrediction.js";
import type { TriangulationResult } from "../domain/entities/FullReport.js";

export class MlService implements IMlService {
  private readonly client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 60_000,
      headers: { "Content-Type": "application/json" },
    });
  }

  async health(): Promise<Record<string, unknown>> {
    const { data } = await this.client.get("/health");
    return data;
  }

  async predict(pitch: GamePitch): Promise<MlPredictionResult> {
    const { data } = await this.client.post<MlPredictionResult>("/predict", pitch);
    return data;
  }

  async triangulate(pitch: GamePitch): Promise<TriangulationResult> {
    const { data } = await this.client.post<TriangulationResult>(
      "/triangulate",
      pitch
    );
    return data;
  }
}
