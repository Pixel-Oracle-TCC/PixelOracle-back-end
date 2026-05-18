/**
 * Integração com Google Gemini — dicas comerciais pré-lançamento.
 */

import { GoogleGenerativeAI } from "@google/generative-ai";
import type { GamePitch } from "../domain/entities/GamePitch.js";
import type { CommercialInsights } from "../domain/entities/FullReport.js";
import type { MlPredictionResult } from "../domain/entities/MlPrediction.js";
import type { IInsightsService } from "../domain/ports/IInsightsService.js";
import { buildCommercialTipsPrompt } from "../infrastructure/prompts/commercialTipsPrompt.js";

export class GeminiService implements IInsightsService {
  private readonly model;

  constructor(apiKey: string, modelName: string) {
    const genAI = new GoogleGenerativeAI(apiKey);
    this.model = genAI.getGenerativeModel({ model: modelName });
  }

  async generateCommercialTips(
    pitch: GamePitch,
    prediction: MlPredictionResult
  ): Promise<CommercialInsights> {
    const prompt = buildCommercialTipsPrompt(pitch, prediction);
    const result = await this.model.generateContent(prompt);
    const text = result.response.text().trim();

    return parseGeminiResponse(text);
  }
}

/** Fallback quando GEMINI_API_KEY não está configurada. */
export class FallbackInsightsService implements IInsightsService {
  async generateCommercialTips(
    pitch: GamePitch,
    prediction: MlPredictionResult
  ): Promise<CommercialInsights> {
    const risco = prediction.previsao_pixel_oracle.risco_comercial;
    const probs = prediction.previsao_pixel_oracle.probabilidades ?? {};
    const pct = formatTopProbability(probs, risco);

    return {
      resumo: `"${pitch.titulo}" foi classificado como "${risco}" no cenário pré-lançamento${pct ? ` (${pct} na classe prevista)` : ""}. Configure GEMINI_API_KEY para análise da sua ideia.`,
      dicas: [
        "Refine o escopo do jogo para combinar com o gênero e o público descrito no pitch.",
        "Alinhe página Steam, trailer e preço com jogos indie brasileiros do mesmo nicho.",
        "Planeje visibilidade pré-lançamento (demo, wishlist, comunidade) para melhorar as chances na semana 1.",
      ],
      fonte: "fallback",
    };
  }
}

function formatTopProbability(
  probs: Record<string, number>,
  predictedClass: string
): string {
  const value = probs[predictedClass];
  if (value == null) return "";
  return `${Math.round(value * 100)}%`;
}

function parseGeminiResponse(text: string): CommercialInsights {
  try {
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]) as {
        resumo?: string;
        dicas?: string[];
      };
      if (parsed.resumo && Array.isArray(parsed.dicas)) {
        return {
          resumo: parsed.resumo,
          dicas: parsed.dicas.slice(0, 5),
          fonte: "gemini",
        };
      }
    }
  } catch {
    /* usa texto bruto */
  }

  const lines = text.split("\n").filter((l) => l.trim());
  return {
    resumo: lines[0] ?? text,
    dicas: lines.slice(1, 4).map((l) => l.replace(/^[-*\d.]+\s*/, "")),
    fonte: "gemini",
  };
}
