"""Casos de uso: retrieve-similar e analyze (dashboard de evidências de reviews).

Fluxo de /analyze:
  pitch → embedding → jogos similares (pgvector)
        → temas recorrentes nas reviews dos similares (calculado na hora)
        → theme_stats dos gêneros do pitch (pré-calculado)
        → drivers do RF de recomendação (pré-calculado)
        → reviews de referência mais úteis de cada similar
        → TriangulationEngine (dashboard estruturado, sem LLM)

A redação em linguagem natural NÃO acontece aqui — fica na API Node (Gemini).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from sqlalchemy.orm import Session

from absa.significance import compute_theme_stats
from embeddings.encoder import EmbeddingEncoder, get_encoder
from retrieval.review_repository import (
    find_genres,
    load_drivers,
    load_genre_theme_stats,
    load_scope,
    load_themes,
    top_reviews_for_game,
)
from retrieval.similar_games import SimilarGamesRetriever
from triangulation.engine import TriangulationEngine, coverage

# Escopo dos similares tem poucos jogos (k≈5): exige menos menções que o gênero
SIMILAR_MIN_MENTIONS = 3


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


class AnalyzePitchUseCase:
    """Endpoint principal do ml-service (consumido por POST /api/report)."""

    def __init__(
        self,
        encoder: Optional[EmbeddingEncoder] = None,
        retriever: Optional[SimilarGamesRetriever] = None,
        engine: Optional[TriangulationEngine] = None,
    ) -> None:
        self._encoder = encoder or get_encoder()
        self._retriever = retriever or SimilarGamesRetriever()
        self._engine = engine or TriangulationEngine()

    def execute(self, session: Session, pitch: Dict[str, Any]) -> Dict[str, Any]:
        genres = pitch.get("genres") or []

        embedding = self._encoder.encode(pitch["titulo"], pitch["descricao"], genres)
        similar = self._retriever.retrieve(session, embedding, top_k=pitch.get("top_k"))

        themes = load_themes(session)
        reviews, aspects = load_scope(session, [g["id"] for g in similar])
        similar_stats = compute_theme_stats(
            reviews, aspects, themes, min_mentions=SIMILAR_MIN_MENTIONS
        )

        genre_ids = [g.id for g in find_genres(session, genres)]
        genre_stats = load_genre_theme_stats(session, genre_ids)
        drivers = load_drivers(session, genre_ids)

        reference = []
        for game in similar:
            top = top_reviews_for_game(session, game["id"])
            if top["positivas"] or top["negativas"]:
                reference.append(
                    {
                        "jogo": {"id": game["id"], "titulo": game["titulo"], "steam_appid": game["steam_appid"]},
                        **top,
                    }
                )

        dashboard = self._engine.build(
            pitch=pitch,
            similar_games=similar,
            similar_stats=similar_stats,
            genre_stats=genre_stats,
            drivers=drivers,
            reference_reviews=reference,
        )
        return {
            "status": "sucesso",
            "modo": "pre-lancamento",
            "jogo": {
                "titulo": pitch["titulo"],
                "descricao": pitch["descricao"],
                "genres": list(genres),
            },
            "dashboard": dashboard,
            "cobertura": coverage(len(reviews), genre_stats, len(themes)),
            # Rastreabilidade: de onde veio cada tipo de sinal
            "evidencias": {
                "fonte_similares": "pgvector_cosine",
                "fonte_temas": "absa_gemini + cluster_agglomerative",
                "fonte_recorrencia": "wilson + qui_quadrado + benjamini_hochberg",
                "fonte_fatores": "random_forest_permutation_importance",
                "fonte_reviews": "steam_get_app_reviews (sem dados de autor)",
            },
        }
