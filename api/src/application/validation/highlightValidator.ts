import type {
  AnalysisResult,
  DashboardNarrative,
  Highlight,
  NarratedHighlight,
  RawNarrative,
} from "../../domain/entities/FullReport.js";

/**
 * Validador pós-Gemini: cada frase de destaque só pode citar jogos que estão em
 * jogos_exemplo daquele destaque. Se citar outro jogo conhecido do dashboard (ou se a
 * Gemini omitir a frase), entra a frase determinística do ml-service.
 *
 * Limitação: só detecta títulos que existem no dashboard; um jogo totalmente inventado
 * fora desse conjunto não é reconhecido. Por isso o prompt também restringe as fontes.
 */
export function validateNarrative(
  analysis: AnalysisResult,
  raw: RawNarrative,
  fonte: DashboardNarrative["fonte"]
): DashboardNarrative {
  const highlights = [
    ...analysis.dashboard.destaques.elogios,
    ...analysis.dashboard.destaques.reclamacoes,
  ];
  const knownTitles = collectKnownTitles(analysis);
  const byId = new Map(raw.destaques.map((d) => [d.id, d.frase]));
  const motivos: string[] = [];

  const destaques: NarratedHighlight[] = highlights.map((h) => {
    const frase = byId.get(h.id);
    if (!frase) {
      if (fonte === "gemini") motivos.push(`${h.id}: frase ausente`);
      return { id: h.id, frase: h.frase, fonte: "modelo" };
    }
    const invalid = citedOutsideExamples(frase, h, knownTitles);
    if (invalid.length) {
      motivos.push(`${h.id}: citou ${invalid.join(", ")} fora dos jogos-exemplo`);
      return { id: h.id, frase: h.frase, fonte: "modelo" };
    }
    return { id: h.id, frase, fonte: fonte === "gemini" ? "gemini" : "modelo" };
  });

  return {
    resumo: raw.resumo,
    destaques,
    fonte,
    validacao: { frases_substituidas: motivos.length, motivos },
  };
}

function collectKnownTitles(analysis: AnalysisResult): string[] {
  const titles = new Set<string>();
  const dash = analysis.dashboard;
  dash.jogos_similares.forEach((g) => titles.add(g.titulo));
  dash.reviews_referencia.forEach((r) => titles.add(r.jogo.titulo));
  [...dash.destaques.elogios, ...dash.destaques.reclamacoes].forEach((h) =>
    h.jogos_exemplo.forEach((j) => titles.add(j.titulo))
  );
  return [...titles].filter(Boolean);
}

function citedOutsideExamples(frase: string, highlight: Highlight, knownTitles: string[]): string[] {
  const allowed = new Set(highlight.jogos_exemplo.map((j) => normalize(j.titulo)));
  const text = normalize(frase);
  return knownTitles.filter((title) => {
    const norm = normalize(title);
    return !allowed.has(norm) && mentions(text, norm);
  });
}

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function mentions(text: string, title: string): boolean {
  // Títulos muito curtos geram falso positivo ("It", "Ori" dentro de outras palavras)
  if (title.length < 3) return false;
  return ` ${text} `.includes(` ${title} `);
}
