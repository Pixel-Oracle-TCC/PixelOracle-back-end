"""
Script offline: coleta reviews para jogos já no banco.

Conformidade: sanitiza e nunca persiste steamid; UPSERT por recommendationid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.reviews_client import ReviewsClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game, Review  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta reviews Steam (sem steamid)")
    parser.add_argument("--limit-games", type=int, default=20)
    parser.add_argument("--positive", type=int, default=10)
    parser.add_argument("--negative", type=int, default=10)
    parser.add_argument("--recent", type=int, default=10)
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    client = ReviewsClient()
    session = session_scope()
    try:
        games = (
            session.query(Game)
            .filter(Game.steam_appid.isnot(None))
            .limit(args.limit_games)
            .all()
        )
        total = 0
        for i, game in enumerate(games, start=1):
            assert game.steam_appid is not None
            samples = client.collect_sample(
                int(game.steam_appid),
                positive_limit=args.positive,
                negative_limit=args.negative,
                recent_limit=args.recent,
            )
            for sample in samples:
                stmt = insert(Review).values(
                    game_id=game.id,
                    recommendationid=sample["recommendationid"],
                    texto=sample["texto"],
                    recomendada=sample["recomendada"],
                    votos_uteis=sample["votos_uteis"],
                    playtime_at_review=sample["playtime_at_review"],
                    tipo_amostra=sample["tipo_amostra"],
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["recommendationid"])
                session.execute(stmt)
                total += 1
            if i % 5 == 0:
                session.commit()
                print(f"... jogos {i}/{len(games)} | reviews processadas ~{total}")
        session.commit()
        print(f"✅ Coleta concluída. Upserts tentados: {total}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
