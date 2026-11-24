import axios, { type AxiosInstance } from "axios";
import type { GamePitch } from "../domain/entities/GamePitch.js";
import type { AnalysisResult } from "../domain/entities/FullReport.js";
import type { IMlService } from "../domain/ports/IMlService.js";

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

  async analyze(pitch: GamePitch): Promise<AnalysisResult> {
    const { data } = await this.client.post<AnalysisResult>("/analyze", pitch);
    return data;
  }

  async correlationHeatmap(): Promise<Buffer> {
    const { data } = await this.client.get<ArrayBuffer>("/correlation-heatmap", {
      responseType: "arraybuffer",
      timeout: 120_000,
    });
    return Buffer.from(data);
  }
}
