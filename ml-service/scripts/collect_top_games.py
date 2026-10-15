"""
Script offline: popula games na ordem dos mais vendidos, só com a API oficial da Steam.

Ranking: IStoreTopSellersService/GetWeeklyTopSellers (top 100 por receita, por semana e país).
As últimas --weeks semanas são somadas em um ranking único (ver collection.catalog.rank_top_sellers)
e cada jogo novo é completado com o appdetails da Store BR.

Conformidade: só dados de jogo; nenhum endpoint de perfil (ISteamUser/IPlayerService) é chamado.
Retomada: o ranking inteiro é regravado em games.rank_popularidade a cada execução; jogos já no
banco e apps em apps_ignorados não consultam a Store de novo, então rodar outra vez com --limit
continua do próximo jogo do ranking.

Depois: backfill_embeddings.py e collect_reviews.py (que segue a mesma ordem do ranking).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from collection.catalog import (  # noqa: E402
    TopSeller,
    catalog_metadata,
    genre_names,
    rank_top_sellers,
    rejection_reason,
    short_description,
)
from collection.steam_client import SteamClient  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import AppIgnorado, Game, GameGenre, Genre  # noqa: E402

WEEK_SECONDS = 7 * 24 * 3600


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def fetch_weeks(client: SteamClient, weeks: int, country: str) -> tuple[List[List[Dict[str, Any]]], Dict[str, Any]]:
    """Baixa as últimas `weeks` semanas, da atual para trás."""
    all_ranks: List[List[Dict[str, Any]]] = []
    start_date = None
    dates: List[int] = []
    for i in range(weeks):
        response = client.get_weekly_top_sellers(start_date=start_date, country=country)
        ranks = response.get("ranks") or []
        week_start = response.get("start_date")
        if not ranks or not week_start:
            print(f"Sem dados antes de {_iso(dates[-1]) if dates else 'hoje'}; parando em {i} semanas.")
            break
        all_ranks.append(ranks)
        dates.append(int(week_start))
        if (i + 1) % 10 == 0:
            print(f"... {i + 1}/{weeks} semanas (até {_iso(int(week_start))})", flush=True)
        start_date = int(week_start) - WEEK_SECONDS
        time.sleep(0.3)
    periodo = {
        "pais": country,
        "semanas": len(dates),
        "de": _iso(min(dates)) if dates else None,
        "ate": _iso(max(dates)) if dates else None,
    }
    return all_ranks, periodo


def link_genres(session, game_id: int, names: List[str]) -> None:
    for nome in names:
        genre = session.query(Genre).filter_by(nome=nome).one_or_none()
        if genre is None:
            genre = Genre(nome=nome)
            session.add(genre)
            session.flush()
        exists = session.query(GameGenre).filter_by(game_id=game_id, genre_id=genre.id).one_or_none()
        if exists is None:
            session.add(GameGenre(game_id=game_id, genre_id=genre.id))


def insert_game(session, rank: int, seller: TopSeller, data: Dict[str, Any], periodo: Dict[str, Any]) -> int:
    values = dict(
        steam_appid=seller.appid,
        titulo=data.get("name") or seller.name,
        descricao=short_description(data),
        preco_brl=SteamClient.extract_price_brl(data),
        release_year=SteamClient.extract_release_year(data),
        rank_popularidade=rank,
        raw_metadata=catalog_metadata(seller, data, periodo),
    )
    stmt = insert(Game).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["steam_appid"],
        set_={k: getattr(stmt.excluded, k) for k in values if k != "steam_appid"},
    ).returning(Game.id)
    game_id = session.execute(stmt).scalar_one()
    link_genres(session, game_id, genre_names(data))
    return game_id


def ignore_app(session, appid: int, titulo: str, motivo: str) -> None:
    stmt = insert(AppIgnorado).values(steam_appid=appid, titulo=titulo, motivo=motivo)
    session.execute(stmt.on_conflict_do_nothing(index_elements=["steam_appid"]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Popula games pelo ranking de mais vendidos da Steam (top sellers semanal)"
    )
    parser.add_argument("--limit", type=int, default=100, help="Jogos novos a adicionar nesta execução")
    parser.add_argument(
        "--weeks",
        type=int,
        default=52,
        help="Semanas de top sellers somadas no ranking (52 = último ano; histórico vai até 2016)",
    )
    parser.add_argument("--country", default="BR", help="País do ranking (código ISO)")
    parser.add_argument("--skip-free", action="store_true", help="Não adiciona jogos gratuitos")
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    store = SteamClient()
    print(f"📈 Baixando {args.weeks} semanas de top sellers ({args.country})...", flush=True)
    weeks, periodo = fetch_weeks(store, args.weeks, args.country)
    ranking = rank_top_sellers(weeks)
    print(f"🏆 Ranking: {len(ranking)} apps distintos de {periodo['de']} a {periodo['ate']}")
    if not ranking:
        raise SystemExit("Top sellers vazio; nada a fazer.")

    session = session_scope()
    try:
        known = {appid for (appid,) in session.query(Game.steam_appid).filter(Game.steam_appid.isnot(None))}
        ignored = {appid for (appid,) in session.query(AppIgnorado.steam_appid)}
        print(f"🎮 Jogos no banco: {len(known)} | apps já descartados: {len(ignored)}")

        # O ranking depende da janela de semanas: posições antigas não valem mais
        session.execute(update(Game).values(rank_popularidade=None))
        session.commit()

        added = ranked = skipped = failed = 0
        for rank, seller in enumerate(ranking, start=1):
            if seller.appid in known:
                session.execute(
                    update(Game).where(Game.steam_appid == seller.appid).values(rank_popularidade=rank)
                )
                ranked += 1
                continue
            # Esgotado o --limit, o resto do ranking só atualiza a posição dos jogos já no banco
            if seller.appid in ignored or added >= args.limit:
                continue
            if args.skip_free and seller.is_free:
                continue

            try:
                data = store.get_app_details(seller.appid)
            except Exception as exc:  # noqa: BLE001 — um app com falha não derruba a coleta
                print(f"⚠️  #{rank} {seller.name} (appid={seller.appid}): {exc}", flush=True)
                failed += 1
                continue

            motivo = rejection_reason(data)
            if motivo:
                ignore_app(session, seller.appid, seller.name, motivo)
                session.commit()
                ignored.add(seller.appid)
                skipped += 1
                print(f"   ↷ #{rank} {seller.name}: {motivo}", flush=True)
                continue
            assert data is not None

            insert_game(session, rank, seller, data, periodo)
            session.commit()
            known.add(seller.appid)
            added += 1
            print(
                f"... [{added}/{args.limit}] #{rank} {seller.name} "
                f"({seller.semanas} semanas no top 100, melhor posição {seller.melhor_rank})",
                flush=True,
            )

        session.commit()
        print(
            f"✅ Novos: {added} | posição atualizada: {ranked} | descartados: {skipped} | falhas: {failed}"
        )
        if added:
            print("→ Próximos: python scripts/backfill_embeddings.py && python scripts/collect_reviews.py")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
