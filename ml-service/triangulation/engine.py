"""Motor do dashboard — combina jogos similares + temas recorrentes + drivers do RF.

Por quê existe: a Gemini não deve inventar a análise. Este módulo monta o dashboard
estruturado (cada ponto com métricas e citações reais) ANTES de qualquer redação.
A frase de cada destaque sai daqui em versão determinística; a API Node pode pedir à
Gemini para reescrevê-la, e um validador garante que ela só cite os jogos-exemplo.
Ver vault: [[Motor de Triangulacao]] / [[Por que Gemini so redige]].

Dois escopos de evidência:
- "similares": reviews dos jogos mais parecidos com o pitch (mais específico);
- "genero": theme_stats pré-calculado para os gêneros do pitch (mais amostra).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

MAX_DESTAQUES = 6
MAX_POR_ESCOPO = 4
MIN_JOGOS_DISTINTOS = 2
SHORT_PLAYTIME_ALERT = 0.5
EARLY_ACCESS_ALERT = 0.5
LOW_SCORE_THRESHOLD = 0.7

METRIC_FIELDS = (
    "reviews_com_tema",
    "total_reviews",
    "prevalencia",
    "wilson_low",
    "wilson_high",
    "jogos_distintos",
    "total_jogos",
    "votos_uteis",
    "pct_recomendadas_com_tema",
    "p_value_ajustado",
    "log_odds",
    "significativo",
)


class TriangulationEngine:
    def build(
        self,
        *,
        pitch: Dict[str, Any],
        similar_games: Sequence[Dict[str, Any]],
        similar_stats: Sequence[Dict[str, Any]],
        genre_stats: Sequence[Dict[str, Any]],
        drivers: Sequence[Dict[str, Any]],
        reference_reviews: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        candidates = self._candidates(similar_stats, "similares") + self._candidates(
            self._dedupe_genre_stats(genre_stats), "genero"
        )
        elogios = self._select(candidates, "positivo")
        reclamacoes = self._select(candidates, "negativo")

        return {
            "destaques": {"elogios": elogios, "reclamacoes": reclamacoes},
            "fatores_decisivos": list(drivers),
            "alertas": self._alerts(reclamacoes, similar_games, similar_stats, genre_stats),
            "reviews_referencia": list(reference_reviews),
            "jogos_similares": list(similar_games),
        }

    @staticmethod
    def _dedupe_genre_stats(stats: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pitch com vários gêneros: o mesmo tema aparece em cada um → fica o de maior amostra."""
        best: Dict[int, Dict[str, Any]] = {}
        for stat in stats:
            current = best.get(stat["theme_id"])
            if current is None or stat["total_reviews"] > current["total_reviews"]:
                best[stat["theme_id"]] = stat
        return list(best.values())

    def _candidates(self, stats: Sequence[Dict[str, Any]], escopo: str) -> List[Dict[str, Any]]:
        result = []
        for stat in stats:
            # Tema de um jogo só é problema daquele jogo, não padrão do mercado
            if (stat.get("jogos_distintos") or 0) < MIN_JOGOS_DISTINTOS:
                continue
            result.append(self._to_highlight(stat, escopo))
        result.sort(key=lambda h: (-h["metricas"]["prevalencia"], -h["metricas"]["votos_uteis"]))
        return result

    @staticmethod
    def _select(candidates: Sequence[Dict[str, Any]], polaridade: str) -> List[Dict[str, Any]]:
        """Similares primeiro (mais específico); gênero completa sem repetir tema."""
        chosen: List[Dict[str, Any]] = []
        seen_themes: set[int] = set()
        for escopo in ("similares", "genero"):
            count = 0
            for highlight in candidates:
                if highlight["escopo"] != escopo or highlight["tema"]["polaridade"] != polaridade:
                    continue
                theme_id = highlight["tema"]["theme_id"]
                if theme_id in seen_themes or count >= MAX_POR_ESCOPO:
                    continue
                chosen.append(highlight)
                seen_themes.add(theme_id)
                count += 1
        return chosen[:MAX_DESTAQUES]

    def _to_highlight(self, stat: Dict[str, Any], escopo: str) -> Dict[str, Any]:
        metricas = {field: stat.get(field) for field in METRIC_FIELDS}
        highlight = {
            "id": f"{escopo}:{stat.get('genero', 'similares')}:{stat['theme_id']}",
            "escopo": escopo,
            "genero": stat.get("genero"),
            "tema": {
                "theme_id": stat["theme_id"],
                "rotulo": stat.get("rotulo"),
                "categoria": stat.get("categoria"),
                "polaridade": stat.get("polaridade"),
            },
            "jogos_exemplo": stat.get("jogos_exemplo") or [],
            "metricas": metricas,
            "citacoes": stat.get("citacoes") or [],
            "contexto": stat.get("contexto") or {},
        }
        highlight["frase"] = template_sentence(highlight)
        return highlight

    @staticmethod
    def _alerts(
        reclamacoes: Sequence[Dict[str, Any]],
        similar_games: Sequence[Dict[str, Any]],
        similar_stats: Sequence[Dict[str, Any]],
        genre_stats: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        if not similar_stats and not genre_stats:
            alerts.append(
                {
                    "tipo": "dados_insuficientes",
                    "mensagem": "Ainda não há reviews analisadas para os jogos similares nem para os gêneros informados.",
                    "evidencia": {},
                }
            )
        for highlight in reclamacoes:
            contexto = highlight.get("contexto") or {}
            rotulo = highlight["tema"]["rotulo"]
            if (contexto.get("pct_menos_2h") or 0) >= SHORT_PLAYTIME_ALERT:
                alerts.append(
                    {
                        "tipo": "primeiras_horas",
                        "mensagem": f"A reclamação '{rotulo}' aparece sobretudo em quem jogou menos de 2h: afeta a primeira impressão.",
                        "evidencia": {"destaque_id": highlight["id"], "pct_menos_2h": contexto.get("pct_menos_2h")},
                    }
                )
            if (contexto.get("pct_early_access") or 0) >= EARLY_ACCESS_ALERT:
                alerts.append(
                    {
                        "tipo": "early_access",
                        "mensagem": f"A reclamação '{rotulo}' se concentra em reviews feitas durante o early access.",
                        "evidencia": {"destaque_id": highlight["id"], "pct_early_access": contexto.get("pct_early_access")},
                    }
                )
        scored = [g for g in similar_games if g.get("pct_positivas") is not None]
        low = [g for g in scored if g["pct_positivas"] < LOW_SCORE_THRESHOLD]
        if scored and len(low) * 2 > len(scored):
            alerts.append(
                {
                    "tipo": "nicho_exigente",
                    "mensagem": f"{len(low)} de {len(scored)} jogos similares têm menos de 70% de reviews positivas na Steam.",
                    "evidencia": {"jogos": [{"titulo": g["titulo"], "pct_positivas": g["pct_positivas"]} for g in low]},
                }
            )
        return alerts


def template_sentence(highlight: Dict[str, Any]) -> str:
    """Frase determinística (fallback e referência para o validador da Gemini)."""
    metricas = highlight["metricas"]
    rotulo = highlight["tema"]["rotulo"]
    pct = round((metricas.get("prevalencia") or 0) * 100)
    jogos = metricas.get("jogos_distintos") or 0
    exemplos = [j["titulo"] for j in highlight.get("jogos_exemplo", [])[:2] if j.get("titulo")]
    exemplos_txt = f", como em {' e '.join(exemplos)}" if exemplos else ""
    escopo_txt = (
        "dos jogos similares ao seu"
        if highlight["escopo"] == "similares"
        else f"de {highlight.get('genero') or 'jogos do gênero'}"
    )
    if highlight["tema"]["polaridade"] == "positivo":
        return (
            f"Jogadores valorizam {rotulo}: o tema aparece em {pct}% das reviews {escopo_txt}, "
            f"em {jogos} jogos diferentes{exemplos_txt}."
        )
    return (
        f"Reclamação recorrente: {rotulo}. Citada em {pct}% das reviews {escopo_txt}, "
        f"em {jogos} jogos diferentes{exemplos_txt}."
    )


def coverage(
    similar_reviews: int, genre_stats: Sequence[Dict[str, Any]], themes_total: int
) -> Dict[str, Optional[int]]:
    genre_reviews = max((s.get("total_reviews") or 0 for s in genre_stats), default=0)
    return {
        "reviews_analisadas_similares": similar_reviews,
        "reviews_analisadas_genero": genre_reviews,
        "temas_disponiveis": themes_total,
    }
