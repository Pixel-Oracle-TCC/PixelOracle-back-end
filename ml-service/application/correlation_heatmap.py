"""Heatmap de correlação de variáveis de jogo (IDs numéricos, não one-hot).

Cada combinação gênero × publicadora de um jogo vira uma linha (todas as
IDs entram; preço/reviews se repetem). Também entram data/ano de lançamento,
preço, total de reviews e ranking de popularidade. Sem identificadores
de autor (ToS Steam cláusula 2 + LGPD).
"""

from __future__ import annotations

import io
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

LEADING_COLS: Sequence[str] = (
    "positive_reviews",
    "negative_reviews",
    "genre_id",
    "publisher_id",
    "release_year",
    "release_date",
    "price",
    "total_reviews",
    "rank_popularidade",
)
ROW_ID_COLS: Sequence[str] = ("id", "game_id")
ANNOT_MAX_VARS = 18

GAMES_SQL = """
SELECT
    g.id AS game_id,
    g.total_positive AS positive_reviews,
    g.total_negative AS negative_reviews,
    g.preco_brl AS price,
    g.total_reviews_steam AS total_reviews,
    g.rank_popularidade,
    g.release_year,
    g.release_date
FROM games g
WHERE g.total_positive IS NOT NULL
  AND g.total_negative IS NOT NULL
"""

GENRES_SQL = """
SELECT gg.game_id, gg.genre_id
FROM game_genres gg
"""

PUBLISHERS_SQL = """
SELECT gp.game_id, gp.publisher_id
FROM game_publishers gp
"""


def _read_table(session: Session, sql: str) -> pd.DataFrame:
    rows = session.execute(text(sql)).mappings().all()
    return pd.DataFrame([dict(row) for row in rows])


def _merge_all_ids(
    games: pd.DataFrame, relations: pd.DataFrame, column: str
) -> pd.DataFrame:
    """Expande o jogo em uma linha por ID (não descarta o segundo gênero/publicadora)."""
    if relations.empty or column not in relations.columns:
        return games
    ids = relations.dropna(subset=["game_id", column])
    if ids.empty:
        return games
    return games.merge(ids[["game_id", column]], on="game_id", how="left")


def build_feature_frame(
    games: pd.DataFrame,
    genres: pd.DataFrame,
    publishers: pd.DataFrame,
) -> pd.DataFrame:
    """Monta o quadro numérico com todas as IDs de gênero e publicadora."""
    if games.empty:
        raise ValueError("Não há jogos com contagem de reviews para correlacionar.")

    base = games.copy()
    base = _merge_all_ids(base, genres, "genre_id")
    base = _merge_all_ids(base, publishers, "publisher_id")

    if "release_date" in base.columns:
        base["release_date"] = (
            pd.to_datetime(base["release_date"], errors="coerce") - pd.Timestamp("1970-01-01")
        ).dt.days

    base = base.reset_index(drop=True)
    base = base.drop(columns=[c for c in ROW_ID_COLS if c in base.columns], errors="ignore")
    numeric = base.select_dtypes(include=["number", "bool", "boolean"]).copy()
    for column in ("genre_id", "publisher_id", "price", "total_reviews", "rank_popularidade", "release_year"):
        if column in numeric.columns:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    if numeric.shape[1] < 2:
        raise ValueError("Poucas variáveis numéricas para montar a matriz de correlação.")
    return numeric


def correlation_matrix(features: pd.DataFrame) -> pd.DataFrame:
    corr = features.corr(numeric_only=True)
    ordered = [c for c in LEADING_COLS if c in corr.columns] + [
        c for c in corr.columns if c not in LEADING_COLS
    ]
    return corr.loc[ordered, ordered]


def _figsize(n_vars: int) -> tuple[float, float]:
    cell = 0.55 if n_vars <= ANNOT_MAX_VARS else 0.32
    side = min(max(8.0, n_vars * cell), 36.0)
    return (side, side)


def render_heatmap_png(corr: pd.DataFrame) -> bytes:
    """Renderiza o heatmap em RAM (BytesIO). Fecha a figura para não vazar memória."""
    n_vars = int(corr.shape[0])
    annot = n_vars <= ANNOT_MAX_VARS
    fig, ax = plt.subplots(figsize=_figsize(n_vars))
    try:
        sns.heatmap(
            corr,
            ax=ax,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            annot=annot,
            fmt=".2f",
            square=True,
            linewidths=0.2,
            cbar_kws={"shrink": 0.75, "label": "correlação de Pearson"},
        )
        ax.set_title("Correlação das variáveis do catálogo")
        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        return buf.getvalue()
    finally:
        plt.close(fig)


class CorrelationHeatmapUseCase:
    """Consulta o catálogo e devolve PNG do heatmap de correlação."""

    def execute(self, session: Session) -> bytes:
        games = _read_table(session, GAMES_SQL)
        genres = _read_table(session, GENRES_SQL)
        publishers = _read_table(session, PUBLISHERS_SQL)
        features = build_feature_frame(games, genres, publishers)
        corr = correlation_matrix(features)
        return render_heatmap_png(corr)
