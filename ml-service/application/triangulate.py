"""Casos de uso: retrieve-similar e triangulate.

Orquestra RF + embedding + pgvector + genre_insights.
A redação em linguagem natural NÃO acontece aqui — fica na API Node (Gemini).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from application.predict_risk import PredictCommercialRiskUseCase
from application.registry import ModelRegistry
from embeddings.encoder import EmbeddingEncoder, get_encoder
from models.orm import Genre, GenreInsight
from retrieval.similar_games import SimilarGamesRetriever
from triangulation.engine import TriangulationEngine

logger = logging.getLogger(__name__)


class RetrieveSimilarUseCase:
    """RAG isolado: útil para debug e para o endpoint POST /retrieve-similar."""

    def __init__(
        self,
        encoder: Optional[EmbeddingEncoder] = None,
        retriever: Optional[SimilarGamesRetriever] = None,
    ) -> None:
        self._encoder = encoder or get_encoder()
        self._retriever = retriever or SimilarGamesRetriever()

    def execute(
        self,
        session: Session,
        *,
        titulo: str,
        descricao: str,
        genres: Sequence[str],
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        embedding = self._encoder.encode(titulo, descricao, genres)
        games = self._retriever.retrieve(session, embedding, top_k=top_k)
        return {
            "status": "sucesso",
            "query": {"titulo": titulo, "genres": list(genres)},
            "jogos_similares": games,
            "k": len(games),
        }


class TriangulateUseCase:
    """
    Endpoint principal do ml-service (consumido por POST /api/report).

    Fluxo com DB:
      pitch → RF → embedding → similares → genre_insights → TriangulationEngine

    Fluxo sem DB (execute_without_db):
      só RF + dashboard “oco” + campo aviso — critério de aceite: não quebrar o report.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        encoder: Optional[EmbeddingEncoder] = None,
        retriever: Optional[SimilarGamesRetriever] = None,
        engine: Optional[TriangulationEngine] = None,
    ) -> None:
        self._predict = PredictCommercialRiskUseCase(registry)
        self._encoder = encoder or get_encoder()
        self._retriever = retriever or SimilarGamesRetriever()
        self._engine = engine or TriangulationEngine()

    def execute(self, session: Session, pitch: Dict[str, Any]) -> Dict[str, Any]:
        # 1) Sinal estatístico (mesmo caminho de /predict)
        prediction = self._predict.execute(pitch)
        genres = pitch.get("genres") or []

        # 2) Sinal semântico: pitch → vetor → k jogos históricos
        embedding = self._encoder.encode(
            pitch.get("titulo") or "",
            pitch.get("descricao") or "",
            genres,
        )
        similar = self._retriever.retrieve(session, embedding)

        # 3) Sinal de opinião agregada por gênero (não por usuário)
        insights = self._load_genre_insights(session, genres)

        # 4) Consolida em dashboard com evidências (ainda sem LLM)
        triangulated = self._engine.build(
            pitch=pitch,
            prediction=prediction,
            similar_games=similar,
            genre_insights=insights,
        )

        return {
            "status": "sucesso",
            "modo": "pre-lancamento",
            "jogo": {
                "titulo": pitch.get("titulo"),
                "descricao": pitch.get("descricao"),
            },
            **triangulated,
        }

    def execute_without_db(self, pitch: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: só predição RF, sem RAG/ABSA (DB indisponível)."""
        prediction = self._predict.execute(pitch)
        triangulated = self._engine.build(
            pitch=pitch,
            prediction=prediction,
            similar_games=[],
            genre_insights=[],
        )
        return {
            "status": "sucesso",
            "modo": "pre-lancamento",
            "aviso": "DATABASE_URL ausente — triangulação parcial (só Random Forest).",
            "jogo": {
                "titulo": pitch.get("titulo"),
                "descricao": pitch.get("descricao"),
            },
            **triangulated,
        }

    @staticmethod
    def _load_genre_insights(
        session: Session, genre_names: Sequence[str]
    ) -> List[Dict[str, Any]]:
        """
        Busca insights já calculados offline (ABSA + qui-quadrado).
        Match pelos nomes de gênero do pitch (ex.: "Indie", "Ação").
        p < 0.05 → significativo=True (usado nas heurísticas de oportunidade/risco).
        """
        if not genre_names:
            return []
        normalized = [g.strip() for g in genre_names if g and str(g).strip()]
        if not normalized:
            return []

        stmt = (
            select(GenreInsight, Genre.nome)
            .join(Genre, Genre.id == GenreInsight.genre_id)
            .where(Genre.nome.in_(normalized))
        )
        rows = session.execute(stmt).all()
        results: List[Dict[str, Any]] = []
        for insight, genre_nome in rows:
            results.append(
                {
                    "genero": genre_nome,
                    "aspecto": insight.aspecto,
                    "frequencia_positiva": insight.frequencia_positiva,
                    "frequencia_negativa": insight.frequencia_negativa,
                    "significancia": float(insight.significancia)
                    if insight.significancia is not None
                    else None,
                    "resumo": insight.resumo,
                    "significativo": (
                        float(insight.significancia) < 0.05
                        if insight.significancia is not None
                        else False
                    ),
                }
            )
        return results
