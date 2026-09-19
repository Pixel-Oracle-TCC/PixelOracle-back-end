"""Script offline: backfill de embeddings para games sem vector."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from db.connection import init_engine, session_scope  # noqa: E402
from embeddings.encoder import EmbeddingEncoder  # noqa: E402
from models.orm import Game  # noqa: E402


def main() -> None:
    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    encoder = EmbeddingEncoder()
    session = session_scope()
    try:
        games = session.query(Game).filter(Game.embedding.is_(None)).all()
        print(f"Gerando embeddings para {len(games)} jogos...")
        for i, game in enumerate(games, start=1):
            genre_names = [g.nome for g in game.genres]
            game.embedding = encoder.encode(
                game.titulo, game.descricao or "", genre_names
            )
            if i % 10 == 0:
                session.commit()
                print(f"... {i}/{len(games)}")
        session.commit()
        print("✅ Backfill de embeddings concluído.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
