/**
 * Prompt para REDIGIR o dashboard a partir do objeto triangulado.
 *
 * Por quê tão restritivo: se pedirmos "analise este jogo", a LLM alucina
 * similares/métricas. Aqui ela só narra o JSON já produzido pelo motor.
 * Prompt legado commercialTipsPrompt.ts NÃO está wired — não reativar.
 */
import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { TriangulationResult } from "../../domain/entities/FullReport.js";

export function buildDashboardNarrativePrompt(
  pitch: GamePitch,
  triangulation: TriangulationResult
): string {
  const pred = triangulation.predicao_ml;
  const dash = triangulation.dashboard;

  return `
Você é o redator do Pixel Oracle. Sua tarefa é REDIGIR em português claro o dashboard
já triangulado abaixo. NÃO invente fatos, jogos, métricas ou aspectos que não estejam
no JSON de evidências. Se algo estiver vazio, diga que a evidência é insuficiente.

## Pitch
- Título: ${pitch.titulo}
- Descrição: ${pitch.descricao}
- Gêneros: ${pitch.genres.join(", ")}
- Preço planejado (BRL): ${pitch.price_brl}

## Predição estatística (Random Forest)
${JSON.stringify(pred, null, 2)}

## Dashboard triangulado (evidências)
${JSON.stringify(dash, null, 2)}

Responda APENAS JSON válido (sem markdown):
{
  "resumo": "1 parágrafo ligando risco estatístico + similares + aspectos do gênero",
  "pontos_fortes": ["frase curta baseada em evidência", "..."],
  "pontos_fracos": ["..."],
  "oportunidades": ["..."],
  "riscos": ["..."]
}
`.trim();
}
