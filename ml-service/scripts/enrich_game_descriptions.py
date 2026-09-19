"""
Enriquece games.descricao via Steam Store appdetails (dados de JOGO, não de usuário).

Idempotente: só atualiza descrições vazias/curtas.
Depois rode: python3 scripts/backfill_embeddings.py (force) ou limpe embeddings nulos.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.steam_client import SteamClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich game descriptions from Steam")
    parser.add_argument("--limit", type=int, default=0, help="0 = todos os jogos")
    parser.add_argument(
        "--min-len",
        type=int,
        default=20,
        help="Atualiza se descricao for None ou menor que isso",
    )
    parser.add_argument(
        "--reset-embeddings",
        action="store_true",
        help="Zera embedding ao atualizar descrição (força re-backfill)",
    )
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    client = SteamClient()
    session = session_scope()
    try:
        q = session.query(Game).filter(Game.steam_appid.isnot(None))
        games = q.all()
        if args.limit > 0:
            games = games[: args.limit]

        updated = 0
        skipped = 0
        failed = 0
        for i, game in enumerate(games, start=1):
            current = (game.descricao or "").strip()
            if len(current) >= args.min_len:
                skipped += 1
                continue
            assert game.steam_appid is not None
            try:
                data = client.get_app_details(int(game.steam_appid))
            except Exception as exc:
                print(f"[{i}/{len(games)}] FAIL appid={game.steam_appid}: {exc}")
                failed += 1
                continue
            if not data:
                skipped += 1
                continue
            short = (data.get("short_description") or "").strip()
            # remove tags HTML simples se vier detailed
            if not short:
                detailed = data.get("detailed_description") or ""
                short = detailed.replace("<br>", " ").replace("<br/>", " ")[:800]
            if len(short) < 10:
                skipped += 1
                continue
            game.descricao = short
            if args.reset_embeddings:
                game.embedding = None
            # também preenche release_year / preço se faltarem
            if game.release_year is None:
                game.release_year = SteamClient.extract_release_year(data)
            if game.preco_brl is None:
                game.preco_brl = SteamClient.extract_price_brl(data)
            updated += 1
            if i % 10 == 0:
                session.commit()
                print(f"... {i}/{len(games)} updated={updated} skipped={skipped} failed={failed}")
        session.commit()
        print(f"✅ Enrich concluído. updated={updated} skipped={skipped} failed={failed}")
        if args.reset_embeddings and updated:
            print("→ Rode: python3 scripts/backfill_embeddings.py")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
