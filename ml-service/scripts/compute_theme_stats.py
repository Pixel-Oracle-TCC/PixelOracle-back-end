"""
Script offline: calcula a recorrência de cada tema por gênero e grava em theme_stats.

Rodar depois de cluster_themes.py. Recalcula tudo (DELETE + INSERT por gênero).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from absa.significance import compute_theme_stats  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Genre, ThemeStat  # noqa: E402
from retrieval.review_repository import game_ids_for_genre, load_scope, load_themes  # noqa: E402

PERSISTED_FIELDS = (
    "reviews_com_tema",
    "total_reviews",
    "prevalencia",
    "wilson_low",
    "wilson_high",
    "jogos_distintos",
    "total_jogos",
    "votos_uteis",
    "pct_recomendadas_com_tema",
    "p_value",
    "p_value_ajustado",
    "log_odds",
    "significativo",
    "jogos_exemplo",
    "citacoes",
    "contexto",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recorrência de temas por gênero")
    parser.add_argument("--min-mentions", type=int, default=5)
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    try:
        themes = load_themes(session)
        if not themes:
            raise SystemExit("Nenhum tema encontrado. Rode scripts/cluster_themes.py antes.")

        total_rows = 0
        for genre in session.query(Genre).order_by(Genre.nome).all():
            reviews, aspects = load_scope(session, game_ids_for_genre(session, genre.id))
            stats = compute_theme_stats(reviews, aspects, themes, min_mentions=args.min_mentions)
            session.query(ThemeStat).filter(ThemeStat.genre_id == genre.id).delete()
            for stat in stats:
                session.add(
                    ThemeStat(
                        genre_id=genre.id,
                        theme_id=stat["theme_id"],
                        **{field: stat[field] for field in PERSISTED_FIELDS},
                    )
                )
            session.commit()
            total_rows += len(stats)
            significant = sum(1 for s in stats if s["significativo"])
            print(f"... {genre.nome}: {len(reviews)} reviews | {len(stats)} temas | {significant} significativos")

        print(f"✅ theme_stats atualizado: {total_rows} linhas")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
