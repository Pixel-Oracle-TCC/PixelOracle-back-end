import type { MlPredictionResult } from "./MlPrediction.js";

/** Ponto do dashboard com evidência verificável. */
export interface DashboardPoint {
  ponto: string;
  evidencia: Record<string, unknown>;
}

export interface TriangulationDashboard {
  pontos_fortes: DashboardPoint[];
  pontos_fracos: DashboardPoint[];
  oportunidades: DashboardPoint[];
  riscos: DashboardPoint[];
  jogos_similares: Record<string, unknown>[];
  insights_genero: Record<string, unknown>[];
}

/** Resposta bruta de POST /triangulate no ml-service. */
export interface TriangulationResult {
  status: string;
  modo?: string;
  aviso?: string;
  jogo?: { titulo?: string; descricao?: string };
  predicao_ml: Record<string, unknown> | MlPredictionResult["previsao_pixel_oracle"];
  dashboard: TriangulationDashboard;
  evidencias?: Record<string, string>;
}

/** Texto redigido pela Gemini a partir do objeto triangulado (não do zero). */
export interface DashboardNarrative {
  resumo: string;
  pontos_fortes: string[];
  pontos_fracos: string[];
  oportunidades: string[];
  riscos: string[];
  fonte: "gemini" | "fallback";
}

export interface FullReport {
  status: string;
  modo: "pre-lancamento";
  jogo: {
    titulo: string;
    descricao: string;
  };
  predicao_ml: TriangulationResult["predicao_ml"];
  dashboard: TriangulationDashboard;
  narrativa: DashboardNarrative;
  evidencias?: Record<string, string>;
  aviso?: string;
}

/** @deprecated Mantido para compatibilidade tipada com serviços antigos. */
export interface CommercialInsights {
  resumo: string;
  dicas: string[];
  fonte: "gemini" | "fallback";
}
