"""
Script offline: coleta reviews para jogos já no banco.

Conformidade: sanitiza e nunca persiste steamid; UPSERT por recommendationid.
Retomada: jogos com games.reviews_collected_at preenchido são pulados (use --force para
recoletar). Funciona como o "checkpoint por appid" da metodologia, sem banco extra.
Ordem: rank_popularidade (mais vendidos primeiro); jogos fora do ranking ficam por último.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.reviews_client import DEFAULT_LANGUAGES, ReviewsClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game, Review  # noqa: E402

UPDATABLE_FIELDS = (
    "texto",
    "recomendada",
    "votos_uteis",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "developer_response",
    "timestamp_dev_responded",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta reviews Steam (sem steamid)")
    parser.add_argument("--limit-games", type=int, default=0, help="0 = todos")
    parser.add_argument("--helpful-positive", type=int, default=40)
    parser.add_argument("--helpful-negative", type=int, default=40)
    parser.add_argument("--recent", type=int, default=20)
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help="Códigos de idioma da Steam separados por vírgula",
    )
    parser.add_argument("--force", action="store_true", help="Recoleta jogos já coletados")
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
        if not args.force:
            query = query.filter(Game.reviews_collected_at.is_(None))
        if args.limit_games:
            query = query.limit(args.limit_games)
        games = query.all()
        print(f"🎮 Jogos a coletar: {len(games)}")

        total = 0
        for i, game in enumerate(games, start=1):
            assert game.steam_appid is not None
            try:
                sample = client.collect_sample(
                    int(game.steam_appid),
                    helpful_positive=args.helpful_positive,
                    helpful_negative=args.helpful_negative,
                    recent=args.recent,
                    languages=languages,
                )
            except Exception as exc:  # noqa: BLE001 — um jogo com falha não derruba a coleta
                print(f"⚠️  {game.titulo} (appid={game.steam_appid}): {exc}")
                continue

            for review in sample.reviews:
                stmt = insert(Review).values(game_id=game.id, **review)
                # Votos e resposta do dev mudam com o tempo; o texto pode ser editado
                stmt = stmt.on_conflict_do_update(
                    index_elements=["recommendationid"],
                    set_={f: getattr(stmt.excluded, f) for f in UPDATABLE_FIELDS},
                )
                session.execute(stmt)
            total += len(sample.reviews)

            summary = sample.summary
            if summary:
                game.total_positive = summary.get("total_positive")
                game.total_negative = summary.get("total_negative")
                game.total_reviews_steam = summary.get("total_reviews")
                game.review_score_desc = summary.get("review_score_desc")
            game.reviews_collected_at = datetime.utcnow()
            # Commit por jogo: se cair no meio, a retomada continua do próximo appid
            session.commit()
            print(
                f"... [{i}/{len(games)}] {game.titulo}: {len(sample.reviews)} reviews "
                f"({summary.get('review_score_desc', 's/ resumo')})"
            )

        print(f"✅ Coleta concluída. Reviews gravadas/atualizadas: {total}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
