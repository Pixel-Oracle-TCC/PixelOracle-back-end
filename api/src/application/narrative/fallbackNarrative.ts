import type { GamePitch } from "../../domain/entities/GamePitch.js";
import type { AnalysisResult, RawNarrative } from "../../domain/entities/FullReport.js";

/** Narrativa sem LLM: resumo a partir das contagens + frases determinísticas do ml-service. */
export function buildFallbackNarrative(pitch: GamePitch, analysis: AnalysisResult): RawNarrative {
  const { elogios, reclamacoes } = analysis.dashboard.destaques;
  const all = [...elogios, ...reclamacoes];
  const resumo = all.length
    ? `"${pitch.titulo}": ${elogios.length} elogio(s) e ${reclamacoes.length} reclamação(ões) ` +
      `recorrentes encontrados em ${analysis.cobertura.reviews_analisadas_similares} reviews de ` +
      `jogos similares e ${analysis.cobertura.reviews_analisadas_genero} reviews do gênero.`
    : `"${pitch.titulo}": ainda não há reviews analisadas suficientes para jogos parecidos.`;
  return { resumo, destaques: all.map((h) => ({ id: h.id, frase: h.frase })) };
}
