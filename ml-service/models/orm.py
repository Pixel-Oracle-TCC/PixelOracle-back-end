"""Modelos ORM SQLAlchemy — schema PostgreSQL + pgvector.

Conformidade: Review não possui campo steamid / identificação de autor.
Deduplicação de reviews por recommendationid.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    owners_estimados: Mapped[Optional[int]] = mapped_column(Integer)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    genres: Mapped[List["Genre"]] = relationship(
        "Genre", secondary="game_genres", back_populates="games"
    )
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="game")


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    games: Mapped[List[Game]] = relationship(
        "Game", secondary="game_genres", back_populates="genres"
    )
    insights: Mapped[List["GenreInsight"]] = relationship(
        "GenreInsight", back_populates="genre"
    )


class GameGenre(Base):
    __tablename__ = "game_genres"

    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


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
    votos_uteis: Mapped[Optional[int]] = mapped_column(Integer)
    playtime_at_review: Mapped[Optional[int]] = mapped_column(Integer)
    tipo_amostra: Mapped[Optional[str]] = mapped_column(Text)
    aspecto: Mapped[Optional[str]] = mapped_column(Text)
    sentimento: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game: Mapped[Game] = relationship("Game", back_populates="reviews")


class GenreInsight(Base):
    __tablename__ = "genre_insights"
    __table_args__ = (UniqueConstraint("genre_id", "aspecto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE")
    )
    aspecto: Mapped[Optional[str]] = mapped_column(Text)
    frequencia_positiva: Mapped[int] = mapped_column(Integer, default=0)
    frequencia_negativa: Mapped[int] = mapped_column(Integer, default=0)
    significancia: Mapped[Optional[float]] = mapped_column(Numeric)
    resumo: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    genre: Mapped[Genre] = relationship("Genre", back_populates="insights")


class TriangulationReport(Base):
    __tablename__ = "triangulation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    projeto_pitch: Mapped[Optional[dict]] = mapped_column(JSONB)
    resultado: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AbsaGoldStandard(Base):
    __tablename__ = "absa_gold_standard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE")
    )
    aspecto_anotador1: Mapped[Optional[str]] = mapped_column(Text)
    sentimento_anotador1: Mapped[Optional[str]] = mapped_column(Text)
    aspecto_anotador2: Mapped[Optional[str]] = mapped_column(Text)
    sentimento_anotador2: Mapped[Optional[str]] = mapped_column(Text)
    aspecto_gemini: Mapped[Optional[str]] = mapped_column(Text)
    sentimento_gemini: Mapped[Optional[str]] = mapped_column(Text)
