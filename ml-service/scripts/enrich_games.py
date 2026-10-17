"""
Script offline: completa metadados Steam dos jogos já no banco via appdetails.

Preenche release_date, preço, descrição, gêneros, categorias, desenvolvedoras,
publicadoras e idiomas. UPSERT por steam_appid; vínculos N:N são idempotentes.

Uso: python scripts/enrich_games.py [--limit 0] [--force]
      --force atualiza mesmo jogos que já têm release_date.
Linguagem da Store: portuguese (pt-PT) por padrão, alinhada aos nomes canônicos
de gênero; país BR para preço em reais.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.catalog import parse_release_date, short_description  # noqa: E402
from collection.game_links import link_from_appdetails  # noqa: E402
from collection.steam_client import SteamClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Enriquece games via Steam appdetails")
    parser.add_argument("--limit", type=int, default=0, help="0 = todos")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconsulta jogos que já têm release_date",
    )
    parser.add_argument("--language", default="portuguese", help="l= da Store")
    parser.add_argument("--country", default="BR", help="cc= da Store")
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    client = SteamClient()
    session = session_scope()
    try:
        query = session.query(Game).filter(Game.steam_appid.isnot(None)).order_by(
            Game.rank_popularidade.asc().nulls_last(), Game.id
        )
        if not args.force:
            query = query.filter(Game.release_date.is_(None))
        if args.limit:
            query = query.limit(args.limit)
        games = query.all()
        print(f"🎮 Jogos a enriquecer: {len(games)} (l={args.language}, cc={args.country})")

        updated = failed = skipped = 0
        for i, game in enumerate(games, start=1):
            assert game.steam_appid is not None
            try:
                data = client.get_app_details(
                    int(game.steam_appid),
                    country=args.country,
                    language=args.language,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️  {game.titulo} (appid={game.steam_appid}): {exc}", flush=True)
                failed += 1
                continue
            if not data:
                skipped += 1
                print(f"   ↷ {game.titulo}: sem appdetails", flush=True)
                continue

            release = parse_release_date(data)
            game.titulo = data.get("name") or game.titulo
            game.descricao = short_description(data) or game.descricao
            game.preco_brl = SteamClient.extract_price_brl(data)
            game.release_date = release
            if release:
                game.release_year = release.year
            elif game.release_year is None:
                game.release_year = SteamClient.extract_release_year(data)
            link_from_appdetails(session, game.id, data)
            session.commit()
            updated += 1
            if i % 10 == 0 or i == len(games):
                print(f"... [{i}/{len(games)}] updated={updated} skipped={skipped} failed={failed}", flush=True)

        print(f"✅ Enrich concluído. updated={updated} skipped={skipped} failed={failed}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
