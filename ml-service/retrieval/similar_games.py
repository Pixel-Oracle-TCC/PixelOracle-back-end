"""Recuperação de jogos similares via pgvector (distância de cosseno).

Por quê pgvector no Postgres (e não FAISS/Pinecone): um único banco relacional+vetorial,
SQL auditável no TCC. Ver vault: [[Por que MiniLM e pgvector]].
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SimilarGamesRetriever:
    """Query ORDER BY embedding <=> :query LIMIT k."""

    def __init__(self, top_k: Optional[int] = None) -> None:
        self.top_k = top_k or int(os.getenv("SIMILAR_GAMES_TOP_K", "5"))

    def retrieve(
        self,
        session: Session,
        query_embedding: Sequence[float],
        *,
        top_k: Optional[int] = None,
        exclude_appids: Optional[Sequence[int]] = None,
    ) -> List[Dict[str, Any]]:
        k = top_k or self.top_k
        # pgvector aceita literal textual '[v1,v2,...]' no CAST AS vector
        vector_literal = "[" + ",".join(str(float(v)) for v in query_embedding) + "]"

        exclude_clause = ""
        params: Dict[str, Any] = {"k": k, "query": vector_literal}
        if exclude_appids:
            exclude_clause = "AND steam_appid NOT IN :exclude"
            params["exclude"] = tuple(exclude_appids)

        # Operador <=> = distância de cosseno (com embeddings normalizados no encoder).
        # similaridade reportada = 1 - distância (mais legível no dashboard: ~1 = muito parecido).
        sql = text(
            f"""
            SELECT
                id,
                steam_appid,
                titulo,
                descricao,
                preco_brl,
                release_year,
                owners_estimados,
                total_positive,
                total_reviews_steam,
                review_score_desc,
                1 - (embedding <=> CAST(:query AS vector)) AS similaridade
            FROM games
            WHERE embedding IS NOT NULL
            {exclude_clause}
            ORDER BY embedding <=> CAST(:query AS vector)
            LIMIT :k
            """
        )

        try:
            rows = session.execute(sql, params).mappings().all()
        except Exception as exc:
            logger.error("Falha na busca vetorial: %s", exc)
            raise

        results: List[Dict[str, Any]] = []
        for row in rows:
            total = row["total_reviews_steam"]
            positive = row["total_positive"]
            results.append(
                {
                    "id": row["id"],
                    "steam_appid": row["steam_appid"],
                    "titulo": row["titulo"],
                    # Truncar descrição: evita payload gigante no /analyze
                    "descricao": (row["descricao"] or "")[:500],
                    "preco_brl": float(row["preco_brl"]) if row["preco_brl"] is not None else None,
                    "release_year": row["release_year"],
                    "owners_estimados": row["owners_estimados"],
                    # Avaliação real da Steam (query_summary), não estimativa
                    "review_score_desc": row["review_score_desc"],
                    "total_reviews_steam": total,
                    "pct_positivas": round(positive / total, 4) if total and positive is not None else None,
                    "similaridade": round(float(row["similaridade"]), 4),
                }
            )
        return results
