"""Motor de triangulação — combina RF + jogos similares + genre_insights.

Por quê existe: a Gemini não deve inventar a análise. Este módulo monta um
dashboard estruturado (com evidência por ponto) ANTES de qualquer redação.
Ver vault: [[Motor de Triangulacao]] / [[Por que Gemini so redige]].
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


class TriangulationEngine:
    """
    Consolida três fontes de evidência em um dashboard estruturado
    ANTES de qualquer redação pela Gemini.

    Fontes:
    1. prediction — saída do Random Forest (risco / probs)
    2. similar_games — RAG via pgvector
    3. genre_insights — aspectos agregados por gênero (ABSA offline)
    """

    def build(
        self,
        *,
        pitch: Dict[str, Any],
        prediction: Dict[str, Any],
        similar_games: Sequence[Dict[str, Any]],
        genre_insights: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        riscos_pred = (
            (prediction.get("previsao_pixel_oracle") or {}).get("risco_comercial")
            or "desconhecido"
        )
        chance = (prediction.get("previsao_pixel_oracle") or {}).get(
            "chance_sucesso_estimada_pct"
        )

        # Heurísticas determinísticas: cada ponto carrega "evidencia" para auditoria
        # no frontend/TCC. Limite [:8] evita dashboard enorme sem ganho analítico.
        pontos_fortes = self._strengths(genre_insights, similar_games)
        pontos_fracos = self._weaknesses(genre_insights, riscos_pred)
        oportunidades = self._opportunities(pitch, similar_games, genre_insights)
        riscos = self._risks(riscos_pred, chance, genre_insights, similar_games)

        return {
            "predicao_ml": prediction.get("previsao_pixel_oracle") or prediction,
            "dashboard": {
                "pontos_fortes": pontos_fortes,
                "pontos_fracos": pontos_fracos,
                "oportunidades": oportunidades,
                "riscos": riscos,
                # Listas brutas: a API Node / Gemini podem citar sem recalcular
                "jogos_similares": list(similar_games),
                "insights_genero": list(genre_insights),
            },
            # Rastreabilidade: de onde veio cada tipo de sinal
            "evidencias": {
                "fonte_predicao": "random_forest",
                "fonte_similares": "pgvector_cosine",
                "fonte_aspectos": "genre_insights_absa",
            },
        }

    def _strengths(
        self,
        insights: Sequence[Dict[str, Any]],
        similares: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Aspectos com mais menções positivas + referência ao top similar."""
        items: List[Dict[str, Any]] = []
        for insight in insights:
            pos = int(insight.get("frequencia_positiva") or 0)
            neg = int(insight.get("frequencia_negativa") or 0)
            if pos > neg and pos > 0:
                items.append(
                    {
                        "ponto": f"Aspecto '{insight.get('aspecto')}' bem avaliado no gênero",
                        "evidencia": {
                            "tipo": "genre_insight",
                            "aspecto": insight.get("aspecto"),
                            "frequencia_positiva": pos,
                            "frequencia_negativa": neg,
                            "significancia": insight.get("significancia"),
                        },
                    }
                )
        if similares:
            # Já ordenados por similaridade no retriever (maior primeiro)
            top = similares[0]
            items.append(
                {
                    "ponto": f"Existem referências históricas próximas (ex.: {top.get('titulo')})",
                    "evidencia": {
                        "tipo": "jogo_similar",
                        "titulo": top.get("titulo"),
                        "similaridade": top.get("similaridade"),
                    },
                }
            )
        return items[:8]

    def _weaknesses(
        self, insights: Sequence[Dict[str, Any]], risco: str
    ) -> List[Dict[str, Any]]:
        """Aspectos mais criticados + alerta se o RF classificar Alto Risco."""
        items: List[Dict[str, Any]] = []
        for insight in insights:
            pos = int(insight.get("frequencia_positiva") or 0)
            neg = int(insight.get("frequencia_negativa") or 0)
            if neg > pos and neg > 0:
                items.append(
                    {
                        "ponto": f"Aspecto '{insight.get('aspecto')}' frequentemente criticado no gênero",
                        "evidencia": {
                            "tipo": "genre_insight",
                            "aspecto": insight.get("aspecto"),
                            "frequencia_positiva": pos,
                            "frequencia_negativa": neg,
                            "significancia": insight.get("significancia"),
                        },
                    }
                )
        # Match por substring: labels do RF usam "Alto Risco" / similares
        if "Alto" in str(risco):
            items.append(
                {
                    "ponto": "Modelo estatístico indica risco comercial elevado no cenário pré-lançamento",
                    "evidencia": {"tipo": "predicao_ml", "risco": risco},
                }
            )
        return items[:8]

    def _opportunities(
        self,
        pitch: Dict[str, Any],
        similares: Sequence[Dict[str, Any]],
        insights: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Preço abaixo da média dos similares e aspectos positivos significativos (p<0.05)."""
        items: List[Dict[str, Any]] = []
        price = pitch.get("price_brl")
        if price is not None and similares:
            prices = [
                float(g["preco_brl"])
                for g in similares
                if g.get("preco_brl") is not None
            ]
            if prices:
                avg = sum(prices) / len(prices)
                if float(price) < avg:
                    items.append(
                        {
                            "ponto": "Preço planejado abaixo da média dos jogos similares",
                            "evidencia": {
                                "tipo": "preco",
                                "preco_pitch": price,
                                "preco_medio_similares": round(avg, 2),
                            },
                        }
                    )
        # "significativo" vem do qui-quadrado em absa/significance.py (populando genre_insights)
        for insight in insights:
            if insight.get("significativo") and int(insight.get("frequencia_positiva") or 0) > int(
                insight.get("frequencia_negativa") or 0
            ):
                items.append(
                    {
                        "ponto": f"Enfatizar '{insight.get('aspecto')}' na página Steam / trailer",
                        "evidencia": {
                            "tipo": "genre_insight",
                            "aspecto": insight.get("aspecto"),
                            "significancia": insight.get("significancia"),
                        },
                    }
                )
        return items[:8]

    def _risks(
        self,
        risco: str,
        chance: Optional[float],
        insights: Sequence[Dict[str, Any]],
        similares: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Sempre inclui a classe do RF; alerta se RAG vazio ou aspectos negativos significativos."""
        items: List[Dict[str, Any]] = [
            {
                "ponto": f"Classificação estatística: {risco}",
                "evidencia": {
                    "tipo": "predicao_ml",
                    "risco": risco,
                    "chance_sucesso_estimada_pct": chance,
                },
            }
        ]
        if not similares:
            items.append(
                {
                    "ponto": "Poucos ou nenhum jogo similar encontrado na base histórica",
                    "evidencia": {"tipo": "retrieval", "k": 0},
                }
            )
        for insight in insights:
            if insight.get("significativo") and int(insight.get("frequencia_negativa") or 0) > int(
                insight.get("frequencia_positiva") or 0
            ):
                items.append(
                    {
                        "ponto": f"Risco de rejeição no aspecto '{insight.get('aspecto')}'",
                        "evidencia": {
                            "tipo": "genre_insight",
                            "aspecto": insight.get("aspecto"),
                            "significancia": insight.get("significancia"),
                        },
                    }
                )
        return items[:8]
