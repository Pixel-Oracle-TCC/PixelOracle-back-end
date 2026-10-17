"""Modelos ORM SQLAlchemy — schema PostgreSQL + pgvector.

Conformidade: nenhuma tabela possui steamid / identificação de autor.
Deduplicação de reviews por recommendationid.
Schema: migrations 001–006 em db/migrations/.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    steam_appid: Mapped[Optional[int]] = mapped_column(Integer, unique=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    preco_brl: Mapped[Optional[float]] = mapped_column(Numeric)
    release_year: Mapped[Optional[int]] = mapped_column(Integer)
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    # Posição no ranking de mais vendidos da Steam (top sellers semanal somado; 1 = mais vendido)
    rank_popularidade: Mapped[Optional[int]] = mapped_column(Integer)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(384))
    # query_summary da Steam: agregados públicos, não estimativas
    total_positive: Mapped[Optional[int]] = mapped_column(Integer)
    total_negative: Mapped[Optional[int]] = mapped_column(Integer)
    total_reviews_steam: Mapped[Optional[int]] = mapped_column(Integer)
    review_score: Mapped[Optional[int]] = mapped_column(Integer)
    review_score_desc: Mapped[Optional[str]] = mapped_column(Text)
    reviews_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Amostra estratificada: collect_reviews só processa na_amostra = True
    na_amostra: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # False se total_reviews_steam < mínimo (fora de theme_stats / drivers)
    elegivel_metricas: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    genres: Mapped[List["Genre"]] = relationship(
        "Genre", secondary="game_genres", back_populates="games"
    )
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="game")


class AppIgnorado(Base):
    """App do ranking que não entra no catálogo (software, DLC, fora da Store BR)."""

    __tablename__ = "apps_ignorados"

    steam_appid: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[Optional[str]] = mapped_column(Text)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    games: Mapped[List[Game]] = relationship(
        "Game", secondary="game_genres", back_populates="genres"
    )


class GameGenre(Base):
    __tablename__ = "game_genres"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    steam_category_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)


class GameCategory(Base):
    __tablename__ = "game_categories"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class GameDeveloper(Base):
    __tablename__ = "game_developers"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    developer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("developers.id", ondelete="CASCADE"), primary_key=True
    )


class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class GamePublisher(Base):
    __tablename__ = "game_publishers"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    publisher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("publishers.id", ondelete="CASCADE"), primary_key=True
    )


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class GameLanguage(Base):
    __tablename__ = "game_languages"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True
    )


class ReviewSnapshot(Base):
    """Totais oficiais de reviews no tempo (ponto zero / review bombing). Sem autor."""

    __tablename__ = "review_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    total_positive: Mapped[Optional[int]] = mapped_column(Integer)
    total_negative: Mapped[Optional[int]] = mapped_column(Integer)
    total_reviews: Mapped[Optional[int]] = mapped_column(Integer)
    review_score: Mapped[Optional[int]] = mapped_column(Integer)
    review_score_desc: Mapped[Optional[str]] = mapped_column(Text)
    total_positive_unfiltered: Mapped[Optional[int]] = mapped_column(Integer)
    total_negative_unfiltered: Mapped[Optional[int]] = mapped_column(Integer)
    total_reviews_unfiltered: Mapped[Optional[int]] = mapped_column(Integer)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Review(Base):
    """
    Review pública sem identificação de autor.

    CONFORMIDADE: não existe coluna steamid / author_id.
    Deduplicação e UPSERT usam recommendationid (unique).
    Ver collection/reviews_client.sanitize_review.
    """

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE")
    )
    # Chave de dedup — NUNCA usar steamid do autor no lugar disso
    recommendationid: Mapped[Optional[str]] = mapped_column(String, unique=True)
    texto: Mapped[Optional[str]] = mapped_column(Text)
    recomendada: Mapped[Optional[bool]] = mapped_column(Boolean)
    # votes_up da Steam ("útil")
    votos_uteis: Mapped[Optional[int]] = mapped_column(Integer)
    votes_funny: Mapped[Optional[int]] = mapped_column(Integer)
    weighted_vote_score: Mapped[Optional[float]] = mapped_column(Numeric)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer)
    playtime_at_review: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[Optional[str]] = mapped_column(Text)
    timestamp_created: Mapped[Optional[int]] = mapped_column(BigInteger)
    early_access: Mapped[Optional[bool]] = mapped_column(Boolean)
    steam_purchase: Mapped[Optional[bool]] = mapped_column(Boolean)
    received_for_free: Mapped[Optional[bool]] = mapped_column(Boolean)
    developer_response: Mapped[Optional[str]] = mapped_column(Text)
    timestamp_dev_responded: Mapped[Optional[int]] = mapped_column(BigInteger)
    # Fatias em que a review foi sorteada (ex.: {proporcional, util_positiva})
    fatias: Mapped[Optional[list]] = mapped_column(ARRAY(Text), default=list)
    absa_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    absa_model: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game: Mapped[Game] = relationship("Game", back_populates="reviews")
    aspects: Mapped[List["ReviewAspect"]] = relationship(
        "ReviewAspect", back_populates="review", cascade="all, delete-orphan"
    )


class Theme(Base):
    """Tema recorrente: cluster de resumos dentro de (categoria, polaridade)."""

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categoria: Mapped[str] = mapped_column(Text, nullable=False)
    polaridade: Mapped[str] = mapped_column(Text, nullable=False)
    rotulo: Mapped[str] = mapped_column(Text, nullable=False)
    tamanho: Mapped[int] = mapped_column(Integer, default=0)
    centroide: Mapped[Optional[Any]] = mapped_column(Vector(384))
    rotulo_fonte: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewAspect(Base):
    """Aspecto extraído de uma review. Sem colunas de autor."""

    __tablename__ = "review_aspects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    categoria: Mapped[str] = mapped_column(Text, nullable=False)
    sentimento: Mapped[str] = mapped_column(Text, nullable=False)
    trecho: Mapped[Optional[str]] = mapped_column(Text)
    # False quando a Gemini devolveu um trecho que não existe no texto → não vira citação
    trecho_literal: Mapped[bool] = mapped_column(Boolean, default=False)
    resumo: Mapped[Optional[str]] = mapped_column(Text)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(384))
    theme_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("themes.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped[Review] = relationship("Review", back_populates="aspects")


class ThemeStat(Base):
    __tablename__ = "theme_stats"
    __table_args__ = (UniqueConstraint("genre_id", "theme_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    reviews_com_tema: Mapped[int] = mapped_column(Integer)
    total_reviews: Mapped[int] = mapped_column(Integer)
    prevalencia: Mapped[Optional[float]] = mapped_column(Numeric)
    wilson_low: Mapped[Optional[float]] = mapped_column(Numeric)
    wilson_high: Mapped[Optional[float]] = mapped_column(Numeric)
    jogos_distintos: Mapped[Optional[int]] = mapped_column(Integer)
    total_jogos: Mapped[Optional[int]] = mapped_column(Integer)
    votos_uteis: Mapped[Optional[int]] = mapped_column(Integer)
    pct_recomendadas_com_tema: Mapped[Optional[float]] = mapped_column(Numeric)
    p_value: Mapped[Optional[float]] = mapped_column(Numeric)
    p_value_ajustado: Mapped[Optional[float]] = mapped_column(Numeric)
    log_odds: Mapped[Optional[float]] = mapped_column(Numeric)
    significativo: Mapped[Optional[bool]] = mapped_column(Boolean)
    jogos_exemplo: Mapped[Optional[list]] = mapped_column(JSONB)
    citacoes: Mapped[Optional[list]] = mapped_column(JSONB)
    contexto: Mapped[Optional[dict]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GenreDriver(Base):
    """Importância de feature no RF de recomendação. genre_id NULL = modelo global."""

    __tablename__ = "genre_drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    genre_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE")
    )
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    rotulo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    importancia: Mapped[Optional[float]] = mapped_column(Numeric)
    importancia_std: Mapped[Optional[float]] = mapped_column(Numeric)
    direcao: Mapped[Optional[str]] = mapped_column(Text)
    taxa_recomendacao_com: Mapped[Optional[float]] = mapped_column(Numeric)
    taxa_recomendacao_sem: Mapped[Optional[float]] = mapped_column(Numeric)
    suporte: Mapped[Optional[int]] = mapped_column(Integer)
    modelo_f1: Mapped[Optional[float]] = mapped_column(Numeric)
    modelo_roc_auc: Mapped[Optional[float]] = mapped_column(Numeric)
    n_amostras: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AbsaGoldStandard(Base):
    """Anotações multi-aspecto: listas JSON de {categoria, sentimento} por anotador."""

    __tablename__ = "absa_gold_standard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), unique=True
    )
    anotador1: Mapped[Optional[list]] = mapped_column(JSONB)
    anotador2: Mapped[Optional[list]] = mapped_column(JSONB)
    consenso: Mapped[Optional[list]] = mapped_column(JSONB)
    gemini: Mapped[Optional[list]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
