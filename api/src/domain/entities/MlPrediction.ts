export interface MlPredictionResult {
  status: string;
  modo?: string;
  jogo?: { titulo: string; descricao: string };
  kpis_analisados: number;
  previsao_pixel_oracle: {
    risco_comercial: string;
    chance_sucesso_estimada_pct?: number | null;
    probabilidades: Record<string, number> | null;
  };
}
