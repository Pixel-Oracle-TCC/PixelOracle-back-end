"""Recorrência de temas em um conjunto de reviews (gênero ou jogos similares).

Para cada tema calcula:
- prevalência (% das reviews que citam o tema) + intervalo de Wilson 95%;
- em quantos jogos distintos aparece (evita confundir problema de um jogo só com padrão);
- votos "útil" somados (peso da comunidade);
- associação com a recomendação: qui-quadrado 2x2 (tema presente/ausente × recomendada
  sim/não) + log-odds com correção de Haldane-Anscombe;
- p-valor ajustado por Benjamini-Hochberg (muitos temas testados ao mesmo tempo);
- jogos-exemplo e citações mais úteis (base dos destaques do dashboard).

Funções puras (sem banco) — usadas por scripts/compute_theme_stats.py (por gênero,
offline) e por application/analyze.py (jogos similares, sob demanda).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from scipy.stats import chi2_contingency

Z_95 = 1.96
SHORT_PLAYTIME_MINUTES = 120


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """IC de Wilson: estável para proporções pequenas e amostras modestas (ao contrário do normal)."""
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def contingency_test(a: int, b: int, c: int, d: int) -> Dict[str, float]:
    """
    Tabela 2x2:
                    recomendada   não recomendada
      com tema           a               b
      sem tema           c               d
    log_odds > 0 → o tema aparece mais em reviews que recomendam o jogo.
    """
    a, b, c, d = (max(int(x), 0) for x in (a, b, c, d))
    log_odds = math.log(((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5)))
    if (a + b) == 0 or (c + d) == 0 or (a + c) == 0 or (b + d) == 0:
        return {"statistic": 0.0, "p_value": 1.0, "log_odds": log_odds}
    try:
        stat, p_value, _, _ = chi2_contingency([[a, b], [c, d]])
    except ValueError:
        return {"statistic": 0.0, "p_value": 1.0, "log_odds": log_odds}
    return {"statistic": float(stat), "p_value": float(p_value), "log_odds": log_odds}


def benjamini_hochberg(p_values: Sequence[float]) -> List[float]:
    """q-valores (FDR). Mantém a ordem de entrada."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_min = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running_min = min(running_min, p_values[i] * m / rank)
        adjusted[i] = min(running_min, 1.0)
    return adjusted


def quote_rank_key(review: Mapping[str, Any]) -> tuple:
    """
    Ordenação de citações/reviews de referência: weighted_vote_score (score de utilidade
    da própria Steam), desempate por votes_up. Review com mais votos "engraçado" que
    "útil" é tratada como meme e vai para o fim.
    """
    votes_up = int(review.get("votos_uteis") or 0)
    votes_funny = int(review.get("votes_funny") or 0)
    is_meme = votes_funny > votes_up
    weighted = float(review.get("weighted_vote_score") or 0.0)
    return (is_meme, -weighted, -votes_up)


def compute_theme_stats(
    reviews: Sequence[Mapping[str, Any]],
    aspects: Iterable[Mapping[str, Any]],
    themes: Mapping[int, Mapping[str, Any]],
    *,
    min_mentions: int = 5,
    alpha: float = 0.05,
    max_examples: int = 3,
    max_quotes: int = 3,
) -> List[Dict[str, Any]]:
    """
    reviews: [{review_id, game_id, game_titulo, recomendada, votos_uteis, votes_funny,
               weighted_vote_score, playtime_at_review, early_access}]
               — TODAS as reviews do escopo (inclusive as sem tema).
    aspects: [{review_id, theme_id, trecho, trecho_literal}]
    themes:  {theme_id: {rotulo, categoria, polaridade}}
    """
    by_review = {r["review_id"]: r for r in reviews}
    total_reviews = len(by_review)
    if total_reviews == 0:
        return []
    total_recommended = sum(1 for r in by_review.values() if r.get("recomendada"))
    reviews_per_game = Counter(r["game_id"] for r in by_review.values())

    theme_reviews: Dict[int, set] = defaultdict(set)
    theme_quotes: Dict[int, Dict[int, str]] = defaultdict(dict)
    for aspect in aspects:
        theme_id = aspect.get("theme_id")
        review_id = aspect.get("review_id")
        if theme_id is None or review_id not in by_review or theme_id not in themes:
            continue
        theme_reviews[theme_id].add(review_id)
        if aspect.get("trecho_literal") and aspect.get("trecho"):
            theme_quotes[theme_id].setdefault(review_id, aspect["trecho"])

    stats: List[Dict[str, Any]] = []
    for theme_id, review_ids in theme_reviews.items():
        k = len(review_ids)
        if k < min_mentions:
            continue
        rows = [by_review[rid] for rid in review_ids]
        recommended_with = sum(1 for r in rows if r.get("recomendada"))
        a = recommended_with
        b = k - recommended_with
        c = total_recommended - recommended_with
        d = (total_reviews - total_recommended) - b
        test = contingency_test(a, b, c, d)
        low, high = wilson_interval(k, total_reviews)

        per_game = Counter(r["game_id"] for r in rows)
        titles = {r["game_id"]: r.get("game_titulo") for r in rows}
        examples = sorted(
            per_game.items(),
            key=lambda item: (-item[1], -(item[1] / reviews_per_game[item[0]])),
        )[:max_examples]

        quoted = sorted(
            (by_review[rid] for rid in theme_quotes[theme_id]),
            key=quote_rank_key,
        )[:max_quotes]

        meta = themes[theme_id]
        stats.append(
            {
                "theme_id": theme_id,
                "rotulo": meta.get("rotulo"),
                "categoria": meta.get("categoria"),
                "polaridade": meta.get("polaridade"),
                "reviews_com_tema": k,
                "total_reviews": total_reviews,
                "prevalencia": round(k / total_reviews, 4),
                "wilson_low": round(low, 4),
                "wilson_high": round(high, 4),
                "jogos_distintos": len(per_game),
                "total_jogos": len(reviews_per_game),
                "votos_uteis": sum(int(r.get("votos_uteis") or 0) for r in rows),
                "pct_recomendadas_com_tema": round(recommended_with / k, 4),
                "p_value": test["p_value"],
                "log_odds": round(test["log_odds"], 4),
                "jogos_exemplo": [
                    {
                        "game_id": game_id,
                        "titulo": titles.get(game_id),
                        "mencoes": count,
                        "prevalencia_no_jogo": round(count / reviews_per_game[game_id], 4),
                    }
                    for game_id, count in examples
                ],
                "citacoes": [
                    {
                        "review_id": r["review_id"],
                        "jogo": r.get("game_titulo"),
                        "trecho": theme_quotes[theme_id][r["review_id"]],
                        "recomendada": bool(r.get("recomendada")),
                        "votos_uteis": int(r.get("votos_uteis") or 0),
                        "horas_jogadas": _hours(r.get("playtime_at_review")),
                    }
                    for r in quoted
                ],
                "contexto": {
                    "pct_menos_2h": round(
                        sum(1 for r in rows if (r.get("playtime_at_review") or 0) < SHORT_PLAYTIME_MINUTES) / k,
                        4,
                    ),
                    "pct_early_access": round(sum(1 for r in rows if r.get("early_access")) / k, 4),
                },
            }
        )

    q_values = benjamini_hochberg([s["p_value"] for s in stats])
    for stat, q in zip(stats, q_values):
        stat["p_value_ajustado"] = round(q, 6)
        stat["p_value"] = round(stat["p_value"], 6)
        stat["significativo"] = q < alpha

    stats.sort(key=lambda s: (-s["prevalencia"], -s["votos_uteis"]))
    return stats


def _hours(minutes: Optional[int]) -> float:
    return round((minutes or 0) / 60, 1)
