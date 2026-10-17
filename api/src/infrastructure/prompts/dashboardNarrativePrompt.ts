/**
 * Prompt para REDIGIR o dashboard a partir das evidências já calculadas.
 *
 * Por quê tão restritivo: se pedirmos "analise este jogo", a LLM alucina jogos e
 * números. Aqui ela só reescreve cada destaque com base no objeto recebido, e o
 * validador (application/validation/highlightValidator.ts) descarta frases que citem
 * jogos fora de jogos_exemplo.
 */
import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { AnalysisResult, Highlight } from "../../domain/entities/FullReport.js";

function compactHighlight(h: Highlight) {
  return {
    id: h.id,
    tipo: h.tema.polaridade === "positivo" ? "elogio" : "reclamacao",
    tema: h.tema.rotulo,
    escopo: h.escopo === "similares" ? "jogos similares ao pitch" : `gênero ${h.genero}`,
    jogos_exemplo: h.jogos_exemplo.map((j) => j.titulo),
    pct_reviews: Math.round(h.metricas.prevalencia * 100),
    jogos_distintos: h.metricas.jogos_distintos,
    citacoes: h.citacoes.map((c) => c.trecho),
    frase_base: h.frase,
  };
}

export function buildDashboardNarrativePrompt(pitch: GamePitch, analysis: AnalysisResult): string {
  const { destaques, fatores_decisivos, alertas, jogos_similares } = analysis.dashboard;
  const highlights = [...destaques.elogios, ...destaques.reclamacoes].map(compactHighlight);

  return `
Você é o redator do Pixel Oracle, que mostra a desenvolvedores indie o que jogadores
elogiam e criticam em jogos parecidos com o deles, com base em reviews reais da Steam.

Regras:
- Use APENAS os dados do JSON. Não invente jogos, números, temas ou citações.
- Em cada destaque, só cite jogos que estão em "jogos_exemplo" daquele destaque.
- Mantenha os percentuais do JSON. Pode reformular, mas sem mudar o sentido.
- Estilo: direto, em português, útil para quem ainda vai lançar o jogo.
  Exemplo de tom: "Muitos jogadores valorizam uma história profunda, como em Hollow Knight
  e Hades, com personagens carismáticos que se desenvolvem durante a gameplay."

## Pitch
- Título: ${pitch.titulo}
- Descrição: ${pitch.descricao}
- Gêneros: ${pitch.genres.join(", ")}

## Destaques (reescreva "frase_base" de cada um, mantendo o id)
${JSON.stringify(highlights, null, 2)}

## Fatores que mais pesam na recomendação (Random Forest)
${JSON.stringify(fatores_decisivos.map((f) => ({ fator: f.rotulo, efeito: f.direcao })), null, 2)}

## Alertas
${JSON.stringify(alertas.map((a) => a.mensagem), null, 2)}

## Jogos similares
${JSON.stringify(jogos_similares.map((g) => g.titulo))}

Responda APENAS JSON válido (sem markdown):
{
  "resumo": "1 parágrafo ligando os principais elogios, reclamações e fatores decisivos ao pitch",
  "destaques": [{ "id": "<id do destaque>", "frase": "..." }]
}
Se não houver destaques, diga no resumo que ainda não há reviews suficientes.
`.trim();
}
