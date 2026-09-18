"""
Gera descricao sintetica a partir de metadados locais (sem chamar Steam).

Use quando store.steampowered.com estiver bloqueada/resetando conexoes.
Melhora o RAG vs titulo vazio: inclui generos, categorias e flags do pitch.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Game  # noqa: E402


def _flags(meta: dict) -> List[str]:
    labels = []
    mapping = [
        ("indie", "indie"),
        ("singleplayer", "singleplayer"),
        ("multiplayer", "multiplayer"),
        ("is_online", "online"),
        ("early_access", "early access"),
        ("is_free", "gratuito"),
    ]
    for key, label in mapping:
        if meta.get(key) is True:
            labels.append(label)
    return labels


def build_synthetic_description(game: Game) -> str:
    meta: dict[str, Any] = game.raw_metadata or {}
    genres = [g.nome for g in game.genres] or meta.get("genres") or []
    if genres and isinstance(genres[0], dict):
        genres = [g.get("description") or g.get("nome") for g in genres]
    cats = meta.get("categories") or []
    if cats and isinstance(cats[0], dict):
        cats = [c.get("description") or c.get("nome") for c in cats]
    cats = [str(c) for c in cats[:8] if c]
    genres_s = ", ".join(str(g) for g in genres if g)
    cats_s = ", ".join(cats)
    flags = ", ".join(_flags(meta))
    year = game.release_year or meta.get("release_year") or ""
    price = game.preco_brl
    price_s = f"Preço histórico ~R${float(price):.2f}." if price is not None else ""
    parts = [
        f"{game.titulo} é um jogo",
        f"de gênero {genres_s}." if genres_s else ".",
        f"Categorias Steam: {cats_s}." if cats_s else "",
        f"Características: {flags}." if flags else "",
        f"Ano de lançamento: {year}." if year else "",
        price_s,
    ]
    return " ".join(p for p in parts if p).strip()


def main() -> None:
    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    try:
        games = session.query(Game).all()
        updated = 0
        for game in games:
            current = (game.descricao or "").strip()
            # só sobrescreve vazio/curto — não apaga descrição real da Steam
            if len(current) >= 40:
                continue
            game.descricao = build_synthetic_description(game)
            game.embedding = None  # força re-backfill
            updated += 1
        session.commit()
        print(f"✅ Descrições sintéticas: {updated}/{len(games)} jogos (embeddings zerados)")
        print("→ Rode: python3 scripts/backfill_embeddings.py")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
