"""
Script offline: upsert de jogos a partir do JSON legado (database_steam_br.json).

Não chama Steam ainda — útil para bootstrap local antes da coleta completa.
Idempotente via steam_appid UNIQUE.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game, GameGenre, Genre  # noqa: E402


def _genres_from_record(rec: Dict[str, Any]) -> List[str]:
    raw = rec.get("genres") or []
    if isinstance(raw, list):
        names = []
        for g in raw:
            if isinstance(g, dict):
                names.append(str(g.get("description") or g.get("nome") or ""))
            else:
                names.append(str(g))
        return [n for n in names if n]
    return []


def _price_brl(rec: Dict[str, Any]) -> float | None:
    overview = rec.get("price_overview") or {}
    if "final" in overview:
        return float(overview["final"]) / 100.0
    if "price_brl" in rec:
        return float(rec["price_brl"])
    return None


def upsert_game(session, rec: Dict[str, Any]) -> None:
    appid = rec.get("app_id") or rec.get("steam_appid") or rec.get("appid")
    titulo = rec.get("name") or rec.get("titulo")
    if not appid or not titulo:
        return

    stmt = insert(Game).values(
        steam_appid=int(appid),
        titulo=str(titulo),
        descricao=rec.get("short_description") or rec.get("descricao") or "",
        preco_brl=_price_brl(rec),
        release_year=rec.get("release_year"),
        raw_metadata=rec,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["steam_appid"],
        set_={
            "titulo": stmt.excluded.titulo,
            "descricao": stmt.excluded.descricao,
            "preco_brl": stmt.excluded.preco_brl,
            "release_year": stmt.excluded.release_year,
            "raw_metadata": stmt.excluded.raw_metadata,
        },
    )
    session.execute(stmt)
    session.flush()

    game = session.query(Game).filter_by(steam_appid=int(appid)).one()
    for nome in _genres_from_record(rec):
        genre = session.query(Genre).filter_by(nome=nome).one_or_none()
        if genre is None:
            genre = Genre(nome=nome)
            session.add(genre)
            session.flush()
        link = (
            session.query(GameGenre)
            .filter_by(game_id=game.id, genre_id=genre.id)
            .one_or_none()
        )
        if link is None:
            session.add(GameGenre(game_id=game.id, genre_id=genre.id))


def main() -> None:
    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")
    data_path = ML_ROOT / "data" / "database_steam_br.json"
    records = json.loads(data_path.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("games") or list(records.values())

    session = session_scope()
    try:
        for i, rec in enumerate(records, start=1):
            upsert_game(session, rec)
            if i % 25 == 0:
                print(f"... {i}/{len(records)}")
        session.commit()
        print(f"✅ Upsert de {len(records)} jogos a partir de {data_path.name}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
