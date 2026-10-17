"""
Script offline: marca games.na_amostra com estratificação por gênero.

Só jogos com na_amostra=TRUE entram em collect_reviews / ABSA.
Prioriza rank_popularidade e exige mínimo de reviews na Steam (default 200).
Jogos abaixo do mínimo ficam com elegivel_metricas=FALSE.

Se total_reviews_steam ainda for NULL, busca o query_summary (num_per_page=0).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import update

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.reviews_client import ReviewsClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game, GameGenre, Genre  # noqa: E402

DEFAULT_MIN_REVIEWS = 200


def main() -> None:
    parser = argparse.ArgumentParser(description="Seleciona amostra estratificada por gênero")
    parser.add_argument("--per-genre", type=int, default=8, help="Mínimo de jogos por gênero")
    parser.add_argument("--total", type=int, default=80, help="Teto da amostra")
    parser.add_argument(
        "--min-reviews",
        type=int,
        default=DEFAULT_MIN_REVIEWS,
        help="Mínimo de total_reviews_steam para entrar na amostra/métricas",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Zera na_amostra em todos os jogos e sai",
    )
    parser.add_argument(
        "--skip-summary-fetch",
        action="store_true",
        help="Não consulta a Steam para preencher total_reviews_steam faltante",
    )
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    client = ReviewsClient(api_key=os.getenv("STEAM_API_KEY") or None)
    try:
        session.execute(update(Game).values(na_amostra=False))
        session.commit()
        if args.clear:
            print("✅ na_amostra zerada em todos os jogos.")
            return

        candidates = (
            session.query(Game)
            .filter(Game.steam_appid.isnot(None))
            .order_by(Game.rank_popularidade.asc().nulls_last(), Game.id)
            .all()
        )

        if not args.skip_summary_fetch:
            missing = [g for g in candidates if g.total_reviews_steam is None]
            print(f"📡 Buscando query_summary de {len(missing)} jogos sem total_reviews_steam...")
            for i, game in enumerate(missing, start=1):
                assert game.steam_appid is not None
                try:
                    summary = client.fetch_summary(int(game.steam_appid))
                except Exception as exc:  # noqa: BLE001
                    print(f"⚠️  {game.titulo}: {exc}", flush=True)
                    continue
                game.total_positive = summary.get("total_positive")
                game.total_negative = summary.get("total_negative")
                game.total_reviews_steam = summary.get("total_reviews")
                game.review_score = summary.get("review_score")
                game.review_score_desc = summary.get("review_score_desc")
                if i % 20 == 0:
                    session.commit()
                    print(f"... {i}/{len(missing)}", flush=True)
            session.commit()

        # Elegibilidade para métricas
        for game in candidates:
            n = game.total_reviews_steam or 0
            game.elegivel_metricas = n >= args.min_reviews
        session.commit()

        eligible = [g for g in candidates if g.elegivel_metricas]
        print(
            f"📊 Elegíveis (≥{args.min_reviews} reviews Steam): "
            f"{len(eligible)}/{len(candidates)}"
        )

        rows = (
            session.query(GameGenre.game_id, Genre.nome)
            .join(Genre, Genre.id == GameGenre.genre_id)
            .filter(GameGenre.game_id.in_([g.id for g in eligible] or [-1]))
            .all()
        )
        genres_of: dict[int, list[str]] = defaultdict(list)
        for game_id, nome in rows:
            if nome not in genres_of[game_id]:
                genres_of[game_id].append(nome)

        by_genre: dict[str, list[Game]] = defaultdict(list)
        for game in eligible:
            for gnome in genres_of.get(game.id) or ["_sem_genero"]:
                by_genre[gnome].append(game)

        selected: set[int] = set()
        for games_list in by_genre.values():
            for game in games_list[: args.per_genre]:
                selected.add(game.id)
                if len(selected) >= args.total:
                    break
            if len(selected) >= args.total:
                break
        for game in eligible:
            if len(selected) >= args.total:
                break
            selected.add(game.id)

        if selected:
            session.execute(update(Game).where(Game.id.in_(selected)).values(na_amostra=True))
            session.commit()

        count_by_genre: dict[str, int] = defaultdict(int)
        for gid in selected:
            for gnome in genres_of.get(gid) or ["_sem_genero"]:
                count_by_genre[gnome] += 1

        print(f"✅ Amostra: {len(selected)} jogos (per-genre≥{args.per_genre}, total≤{args.total})")
        for gnome, n in sorted(count_by_genre.items(), key=lambda x: (-x[1], x[0])):
            print(f"   {gnome}: {n}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
