"""Significância estatística de aspectos (positiva vs negativa) por gênero.

Popula a lógica por trás de genre_insights.significancia.
p_value < 0.05 → TriangulateUseCase marca significativo=True → entra em
oportunidades/riscos do TriangulationEngine.
Qui-quadrado 2x2 + log-odds (Haldane-Anscombe) para estabilidade com células zeradas.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from scipy.stats import chi2_contingency


def chi_square_significance(
    freq_positive: int, freq_negative: int, *, total_positive: int, total_negative: int
) -> Dict[str, float]:
    """
    Qui-quadrado 2x2: aspecto presente vs ausente × review positiva vs negativa.
    Retorna statistic, p_value e log_odds aproximado.
    """
    a = max(freq_positive, 0)
    b = max(freq_negative, 0)
    c = max(total_positive - a, 0)
    d = max(total_negative - b, 0)

    table = [[a, b], [c, d]]
    # Evita tabela degenerada
    if (a + b + c + d) == 0 or (a + b == 0) or (c + d == 0):
        return {"statistic": 0.0, "p_value": 1.0, "log_odds": 0.0}

    try:
        stat, p_value, _, _ = chi2_contingency(table)
    except ValueError:
        return {"statistic": 0.0, "p_value": 1.0, "log_odds": 0.0}

    # Haldane-Anscombe correction para log-odds
    log_odds = math.log(((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5)))
    return {
        "statistic": float(stat),
        "p_value": float(p_value),
        "log_odds": float(log_odds),
    }


def aggregate_aspect_counts(
    rows: List[dict],
) -> Tuple[Dict[str, Dict[str, int]], int, int]:
    """
    rows: {aspecto, sentimento} onde sentimento in positivo|negativo|neutro.
    Retorna (aspecto -> {positiva, negativa}, total_pos, total_neg).
    """
    counts: Dict[str, Dict[str, int]] = {}
    total_pos = 0
    total_neg = 0
    for row in rows:
        sentimento = (row.get("sentimento") or "").lower()
        aspecto = (row.get("aspecto") or "outros").lower()
        if sentimento == "positivo":
            total_pos += 1
            bucket = "positiva"
        elif sentimento == "negativo":
            total_neg += 1
            bucket = "negativa"
        else:
            continue
        if aspecto not in counts:
            counts[aspecto] = {"positiva": 0, "negativa": 0}
        counts[aspecto][bucket] += 1
    return counts, total_pos, total_neg


def build_genre_insights(
    rows: List[dict], *, p_threshold: float = 0.05
) -> List[Dict[str, Optional[float]]]:
    """Gera lista de insights com significância por aspecto."""
    counts, total_pos, total_neg = aggregate_aspect_counts(rows)
    insights: List[Dict[str, Optional[float]]] = []
    for aspecto, freqs in counts.items():
        sig = chi_square_significance(
            freqs["positiva"],
            freqs["negativa"],
            total_positive=total_pos,
            total_negative=total_neg,
        )
        insights.append(
            {
                "aspecto": aspecto,
                "frequencia_positiva": freqs["positiva"],
                "frequencia_negativa": freqs["negativa"],
                "significancia": sig["p_value"],
                "log_odds": sig["log_odds"],
                "significativo": sig["p_value"] < p_threshold,
            }
        )
    return insights
