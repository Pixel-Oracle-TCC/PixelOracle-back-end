import type { MlPredictionResult } from "./MlPrediction.js";

export interface CommercialInsights {
  resumo: string;
  dicas: string[];
  fonte: "gemini" | "fallback";
}

export interface FullReport {
  status: string;
  modo: "pre-lancamento";
  jogo: {
    titulo: string;
    descricao: string;
  };
  predicao_ml: MlPredictionResult;
  insights: CommercialInsights;
}
