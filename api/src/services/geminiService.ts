/**
 * Integração Gemini — redige o dashboard a partir das evidências já calculadas.
 *
 * Dois adapters da mesma port (IInsightsService):
 * - GeminiService: chama a LLM com prompt restritivo
 * - FallbackInsightsService: usa as frases determinísticas do ml-service (sem rede)
 *
 * Sem chave no boot (index.ts) → FallbackInsightsService.
 * Ver vault: [[Por que Gemini so redige]] / [[Por que Ports and Adapters]].
 */

import { GoogleGenerativeAI } from "@google/generative-ai";
import type { GamePitch } from "../domain/entities/GamePitch.js";
import type { AnalysisResult, RawNarrative } from "../domain/entities/FullReport.js";
import type { IInsightsService } from "../domain/ports/IInsightsService.js";
import { buildFallbackNarrative } from "../application/narrative/fallbackNarrative.js";
import { buildDashboardNarrativePrompt } from "../infrastructure/prompts/dashboardNarrativePrompt.js";

export class GeminiService implements IInsightsService {
  private readonly model;

  constructor(apiKey: string, modelName: string) {
    const genAI = new GoogleGenerativeAI(apiKey);
    this.model = genAI.getGenerativeModel({
      model: modelName,
      generationConfig: { responseMimeType: "application/json", temperature: 0.3 },
    });
  }

  async narrateDashboard(pitch: GamePitch, analysis: AnalysisResult): Promise<RawNarrative> {
    const prompt = buildDashboardNarrativePrompt(pitch, analysis);
    const result = await this.model.generateContent(prompt);
    return parseNarrativeResponse(result.response.text().trim());
  }
}

/** Fallback: resumo montado a partir dos dados e frases determinísticas do ml-service. */
export class FallbackInsightsService implements IInsightsService {
  async narrateDashboard(pitch: GamePitch, analysis: AnalysisResult): Promise<RawNarrative> {
    return buildFallbackNarrative(pitch, analysis);
  }
}

/** Extrai JSON da resposta; se a LLM enrolar com markdown, ainda tentamos recuperar. */
function parseNarrativeResponse(text: string): RawNarrative {
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error("Resposta da Gemini sem JSON.");
  }
  const parsed = JSON.parse(jsonMatch[0]) as Partial<RawNarrative>;
  if (!parsed.resumo) {
    throw new Error("Resposta da Gemini sem resumo.");
  }
  const destaques = Array.isArray(parsed.destaques)
    ? parsed.destaques
        .filter((d) => d && typeof d.id === "string" && typeof d.frase === "string")
        .map((d) => ({ id: d.id, frase: d.frase.trim() }))
    : [];
  return { resumo: String(parsed.resumo), destaques };
}
