"""Encoder de embeddings com sentence-transformers (all-MiniLM-L6-v2).

Por quê este modelo: 384 dims, leve para o container do ml-service, bom para
textos curtos (título+descrição). Dimensão deve bater com VECTOR(384) no schema.
Ver vault: [[Por que MiniLM e pgvector]].
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class EmbeddingEncoder:
    """Gera embedding de título + descrição + gêneros."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
        self._model = None

    def _load(self):
        # Lazy load: a 1ª chamada é lenta; evita travar o boot se /predict for o único uso
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Carregando embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build_text(
        self,
        titulo: str,
        descricao: str = "",
        genres: Optional[Sequence[str]] = None,
    ) -> str:
        """Mesmo formato no backfill e na query — inconsistência aqui quebra o RAG."""
        genres_part = ", ".join(genres or [])
        return f"{titulo}. {descricao}. Gêneros: {genres_part}".strip()

    def encode(
        self,
        titulo: str,
        descricao: str = "",
        genres: Optional[Sequence[str]] = None,
    ) -> List[float]:
        text = self.build_text(titulo, descricao, genres)
        model = self._load()
        # normalize_embeddings=True → distância de cosseno do pgvector fica coerente
        vector = model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vector.tolist()]

    def encode_batch(self, texts: Sequence[str]) -> List[List[float]]:
        model = self._load()
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [[float(x) for x in row.tolist()] for row in vectors]


@lru_cache(maxsize=1)
def get_encoder() -> EmbeddingEncoder:
    """Singleton: não recarregar o modelo a cada request."""
    return EmbeddingEncoder()
