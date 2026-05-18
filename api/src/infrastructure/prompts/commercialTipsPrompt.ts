import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { MlPredictionResult } from "../../domain/entities/MlPrediction.js";

export function buildCommercialTipsPrompt(
  pitch: GamePitch,
  prediction: MlPredictionResult
): string {
  const { risco_comercial, probabilidades, chance_sucesso_estimada_pct } =
    prediction.previsao_pixel_oracle;
  const probText = probabilidades
    ? Object.entries(probabilidades)
        .map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`)
        .join(", ")
    : "não disponível";
  const chanceText =
    chance_sucesso_estimada_pct != null
      ? `${chance_sucesso_estimada_pct}% (classe prevista)`
      : "não calculada";

  return `
Você é o assistente Pixel Oracle para desenvolvedores indie brasileiros.

MISSÃO: auxiliar o DESENVOLVIMENTO do jogo e ajudar o dev a entender RISCOS e CHANCES DE SUCESSO comercial ANTES do lançamento na Steam.

REGRAS:
- O jogo AINDA NÃO está publicado. NÃO existem reviews, wishlists reais nem vendas na Steam.
- NÃO sugira analisar comentários de jogadores ou métricas pós-lançamento.
- Tom construtivo: oriente produto, escopo, página Steam, preço e visibilidade.

## Pitch do desenvolvedor
- Título: ${pitch.titulo}
- Ideia / descrição: ${pitch.descricao}

## Planejamento (metadados que o dev pretende na Steam)
- Gêneros: ${pitch.genres.join(", ")}
- Categorias: ${pitch.categories.join(", ")}
- Preço planejado (BRL): ${pitch.price_brl}
- Ano de lançamento previsto: ${pitch.release_year}
- Idiomas: ${pitch.supported_languages ?? 1}
- Conquistas planejadas: ${pitch.achievements ?? 0}
- Indie: ${pitch.indie ?? true} | Early Access: ${pitch.early_access ?? false}

## Análise do modelo (histórico de jogos BR similares — pré-lançamento)
- Risco comercial estimado: ${risco_comercial}
- Chance de sucesso (classe prevista): ${chanceText}
- Distribuição: ${probText}

Com base no pitch e no planejamento, explique o que o resultado significa para o desenvolvimento e liste ações práticas ANTES do lançamento.

Responda APENAS JSON válido (sem markdown):
{
  "resumo": "parágrafo em português: risco, chances e leitura do pitch",
  "dicas": [
    "dica sobre desenvolvimento do jogo ou escopo",
    "dica sobre página Steam / preço / posicionamento",
    "dica sobre visibilidade ou lançamento"
  ]
}
`.trim();
}
