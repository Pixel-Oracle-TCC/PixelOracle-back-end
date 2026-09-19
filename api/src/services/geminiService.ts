/**
 * Integração Gemini — redige dashboard a partir do objeto triangulado.
 *
 * Dois adapters da mesma port (IInsightsService):
 * - GeminiService: chama a LLM com prompt restritivo
 * - FallbackInsightsService: copia os "ponto" do dashboard (sem rede)
 *
 * Sem chave no boot (index.ts) → FallbackInsightsService.
 * Ver vault: [[Por que Gemini so redige]] / [[Por que Ports and Adapters]].
 */

import { GoogleGenerativeAI } from "@google/generative-ai";
import type { GamePitch } from "../domain/entities/GamePitch.js";
import type {
  DashboardNarrative,
  TriangulationResult,
} from "../domain/entities/FullReport.js";
import type { IInsightsService } from "../domain/ports/IInsightsService.js";
import { buildDashboardNarrativePrompt } from "../infrastructure/prompts/dashboardNarrativePrompt.js";

export class GeminiService implements IInsightsService {
  private readonly model;

  constructor(apiKey: string, modelName: string) {
    const genAI = new GoogleGenerativeAI(apiKey);
    this.model = genAI.getGenerativeModel({ model: modelName });
  }

  async narrateDashboard(
    pitch: GamePitch,
    triangulation: TriangulationResult
  ): Promise<DashboardNarrative> {
    const prompt = buildDashboardNarrativePrompt(pitch, triangulation);
    const result = await this.model.generateContent(prompt);
    const text = result.response.text().trim();
    return parseNarrativeResponse(text);
  }
}

/** Fallback: expõe os pontos triangulados brutos sem Gemini. */
export class FallbackInsightsService implements IInsightsService {
  async narrateDashboard(
    pitch: GamePitch,
    triangulation: TriangulationResult
  ): Promise<DashboardNarrative> {
    const dash = triangulation.dashboard;
    const pred = triangulation.predicao_ml as {
      risco_comercial?: string;
      chance_sucesso_estimada_pct?: number;
    };

    return {
      resumo:
        `"${pitch.titulo}" — triangulação disponível sem Gemini. ` +
        `Risco estatístico: ${pred.risco_comercial ?? "n/d"}` +
        (pred.chance_sucesso_estimada_pct != null
          ? ` (${pred.chance_sucesso_estimada_pct}% na classe prevista).`
          : ".") +
        " Configure GEMINI_API_KEY para narrativa redigida.",
      pontos_fortes: dash.pontos_fortes.map((p) => p.ponto).slice(0, 5),
      pontos_fracos: dash.pontos_fracos.map((p) => p.ponto).slice(0, 5),
      oportunidades: dash.oportunidades.map((p) => p.ponto).slice(0, 5),
      riscos: dash.riscos.map((p) => p.ponto).slice(0, 5),
      fonte: "fallback",
    };
  }
}

/** Extrai JSON da resposta; se a LLM enrolar com markdown, ainda tentamos recuperar. */
function parseNarrativeResponse(text: string): DashboardNarrative {
  try {
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]) as Partial<DashboardNarrative>;
      if (parsed.resumo) {
        return {
          resumo: parsed.resumo,
          pontos_fortes: asStringArray(parsed.pontos_fortes),
          pontos_fracos: asStringArray(parsed.pontos_fracos),
          oportunidades: asStringArray(parsed.oportunidades),
          riscos: asStringArray(parsed.riscos),
          fonte: "gemini",
        };
      }
    }
  } catch {
    /* fallback texto bruto */
  }

  return {
    resumo: text.slice(0, 500),
    pontos_fortes: [],
    pontos_fracos: [],
    oportunidades: [],
    riscos: [],
    fonte: "gemini",
  };
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((v) => String(v)).slice(0, 8);
}
