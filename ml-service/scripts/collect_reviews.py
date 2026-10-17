"""
Script offline: coleta reviews para jogos na amostra (na_amostra = TRUE).

Conformidade: sanitiza e nunca persiste steamid; UPSERT por recommendationid.
Ordem: round-robin por gênero (mais vendidos primeiro dentro do gênero) — se a
coleta/ABSA parar no meio, o banco não fica enviesado só para AAA.

Fatias: proporcional (recentes, por idioma) + util_positiva/negativa. Sem dedup
entre fatias — `fatias TEXT[]` acumula. Snapshot dual (com/sem offtopic).

Não paralelize: pausa 1,5 s entre páginas e backoff em 429.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.reviews_client import (  # noqa: E402
    DEFAULT_HELPFUL_NEGATIVE,
    DEFAULT_HELPFUL_POSITIVE,
    DEFAULT_LANGUAGES,
    DEFAULT_PROPORTIONAL_PER_LANGUAGE,
    ReviewsClient,
)
from db.connection import init_engine, session_scope  # noqa: E402
from ml.experiments import log_experiment  # noqa: E402
from models.orm import Game, GameGenre, Genre, Review, ReviewSnapshot  # noqa: E402

UPDATABLE_FIELDS = (
    "texto",
    "recomendada",
    "votos_uteis",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "developer_response",
    "timestamp_dev_responded",
    "steam_purchase",
    "received_for_free",
    "playtime_at_review",
    "timestamp_created",
    "early_access",
    "language",
)


def round_robin_by_genre(session, games: List[Game]) -> List[Game]:
    """Um jogo de cada gênero por vez; dentro do gênero, mais vendidos primeiro."""
    if not games:
        return []
    ids = [g.id for g in games]
    rows = (
        session.query(GameGenre.game_id, Genre.nome)
        .join(Genre, Genre.id == GameGenre.genre_id)
        .filter(GameGenre.game_id.in_(ids))
        .all()
    )
    genres_of: Dict[int, List[str]] = defaultdict(list)
    for game_id, nome in rows:
        if nome not in genres_of[game_id]:
            genres_of[game_id].append(nome)

    # Cada jogo entra na fila do primeiro gênero (alfabético) — evita duplicar
    queues: Dict[str, Deque[Game]] = defaultdict(deque)
    for game in games:
        key = sorted(genres_of.get(game.id) or ["_sem_genero"])[0]
        queues[key].append(game)

    ordered: List[Game] = []
    while any(queues.values()):
        for key in sorted(queues.keys()):
            if queues[key]:
                ordered.append(queues[key].popleft())
    return ordered


def upsert_review(session, game_id: int, review: dict) -> None:
    rid = review["recommendationid"]
    existing = session.query(Review).filter_by(recommendationid=rid).one_or_none()
    new_fatias = list(review.get("fatias") or [])
    if existing is None:
        session.add(Review(game_id=game_id, **review))
        return
    merged = sorted(set((existing.fatias or []) + new_fatias))
    for field in UPDATABLE_FIELDS:
        if field in review and review[field] is not None:
            setattr(existing, field, review[field])
    existing.fatias = merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta reviews Steam (sem steamid)")
    parser.add_argument("--limit-games", type=int, default=0, help="0 = todos da amostra")
    parser.add_argument("--helpful-positive", type=int, default=DEFAULT_HELPFUL_POSITIVE)
    parser.add_argument("--helpful-negative", type=int, default=DEFAULT_HELPFUL_NEGATIVE)
    parser.add_argument(
        "--proportional-per-language",
        type=int,
        default=DEFAULT_PROPORTIONAL_PER_LANGUAGE,
        help="Recentes sem filtro de tipo, POR idioma (default 50 → ~100 com PT+EN)",
    )
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help="Códigos de idioma da Steam separados por vírgula",
    )
    parser.add_argument("--force", action="store_true", help="Recoleta jogos já coletados")
    parser.add_argument(
        "--all-games",
        action="store_true",
        help="Ignora na_amostra e coleta todos os jogos do banco",
    )
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]
    client = ReviewsClient(api_key=os.getenv("STEAM_API_KEY") or None)
    session = session_scope()
    try:
        query = (
            session.query(Game)
            .filter(Game.steam_appid.isnot(None))
            .order_by(Game.rank_popularidade.asc().nulls_last(), Game.id)
        )
        if not args.all_games:
            query = query.filter(Game.na_amostra.is_(True))
        if not args.force:
            query = query.filter(Game.reviews_collected_at.is_(None))
        games = query.all()
        games = round_robin_by_genre(session, games)
        if args.limit_games:
            games = games[: args.limit_games]
        escopo = "todos" if args.all_games else "amostra"
        print(f"🎮 Jogos a coletar ({escopo}, round-robin por gênero): {len(games)}")

        params = {
            "helpful_positive": args.helpful_positive,
            "helpful_negative": args.helpful_negative,
            "proportional_per_language": args.proportional_per_language,
            "languages": languages,
            "ordem": "round_robin_genero",
            "nota_proporcional": (
                "filter=recent (últimas semanas), não vida inteira do jogo; "
                "limite é por idioma"
            ),
        }
        log_experiment(
            "collect_reviews",
            {"parametros": params, "jogos_planejados": len(games),
             "appids": [g.steam_appid for g in games]},
        )

        total = 0
        for i, game in enumerate(games, start=1):
            assert game.steam_appid is not None
            try:
                sample = client.collect_sample(
                    int(game.steam_appid),
                    helpful_positive=args.helpful_positive,
                    helpful_negative=args.helpful_negative,
                    proportional_per_language=args.proportional_per_language,
                    languages=languages,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️  {game.titulo} (appid={game.steam_appid}): {exc}", flush=True)
                continue

            for review in sample.reviews:
                upsert_review(session, game.id, review)
            total += len(sample.reviews)

            summary = sample.summary or {}
            unfiltered = sample.summary_unfiltered or {}
            if summary:
                game.total_positive = summary.get("total_positive")
                game.total_negative = summary.get("total_negative")
                game.total_reviews_steam = summary.get("total_reviews")
                game.review_score = summary.get("review_score")
                game.review_score_desc = summary.get("review_score_desc")
            session.add(
                ReviewSnapshot(
                    game_id=game.id,
                    total_positive=summary.get("total_positive"),
                    total_negative=summary.get("total_negative"),
                    total_reviews=summary.get("total_reviews"),
                    review_score=summary.get("review_score"),
                    review_score_desc=summary.get("review_score_desc"),
                    total_positive_unfiltered=unfiltered.get("total_positive"),
                    total_negative_unfiltered=unfiltered.get("total_negative"),
                    total_reviews_unfiltered=unfiltered.get("total_reviews"),
                    collected_at=datetime.utcnow(),
                )
            )
            game.reviews_collected_at = datetime.utcnow()
            session.commit()
            print(
                f"... [{i}/{len(games)}] {game.titulo}: {len(sample.reviews)} reviews "
                f"({summary.get('review_score_desc', 's/ resumo')})",
                flush=True,
            )

        print(f"✅ Coleta concluída. Reviews gravadas/atualizadas: {total}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
