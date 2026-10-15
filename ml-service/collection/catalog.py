"""Regras do catálogo de jogos: o que entra, com quais gêneros e metadados.

Escopo: dados de jogo (top sellers + appdetails da Steam), nunca de usuário.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

TOP_SELLERS_PER_WEEK = 100
# item.type do top sellers: 4 = DLC; o resto é decidido pelo appdetails
DLC_ITEM_TYPE = 4

# Ids de gênero da Steam que marcam software (Utilitários, Design e ilustração, Edição de vídeo...)
SOFTWARE_GENRE_IDS = {str(i) for i in range(50, 61)}
# Ids que a Steam lista como gênero mas são descritores de conteúdo (nudez, violência, gore)
CONTENT_DESCRIPTOR_GENRE_IDS = {"71", "72", "73", "74"}
# Nomes canônicos por id, iguais aos já gravados no banco (JSON legado em pt-PT); sem isso,
# a Store em pt-BR criaria duplicatas como "Esportes" ao lado de "Desporto"
CANONICAL_GENRE_NAMES = {
    "1": "Ação",
    "2": "Estratégia",
    "3": "RPG",
    "4": "Casual",
    "9": "Corridas",
    "18": "Desporto",
    "23": "Indie",
    "25": "Aventura",
    "28": "Simulação",
    "29": "Multijogador Massivo Online (MMO)",
    "37": "Grátis para Jogar",
    "70": "Acesso Antecipado",
}


def rejection_reason(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Motivo para o app não entrar no catálogo, ou None se é um jogo."""
    if not data:
        return "sem página na Store BR"
    app_type = data.get("type")
    if app_type != "game":
        return f"tipo {app_type}"
    genre_ids = {str(g.get("id")) for g in data.get("genres") or []}
    if genre_ids & SOFTWARE_GENRE_IDS:
        return "software"
    return None


def genre_names(data: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for genre in data.get("genres") or []:
        genre_id = str(genre.get("id"))
        if genre_id in CONTENT_DESCRIPTOR_GENRE_IDS:
            continue
        name = CANONICAL_GENRE_NAMES.get(genre_id) or (genre.get("description") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def short_description(data: Dict[str, Any]) -> str:
    text = (data.get("short_description") or "").strip()
    if text:
        return text
    detailed = data.get("detailed_description") or ""
    return detailed.replace("<br>", " ").replace("<br/>", " ")[:800].strip()


@dataclass
class TopSeller:
    appid: int
    name: str
    is_free: bool
    pontos: int = 0
    semanas: int = 0
    melhor_rank: int = TOP_SELLERS_PER_WEEK + 1


def rank_top_sellers(weeks: Iterable[List[Dict[str, Any]]]) -> List[TopSeller]:
    """
    Junta várias semanas de top sellers num ranking só. Cada semana dá 101 − posição pontos
    (1º = 100, 100º = 1); ordena por pontos, depois semanas no top e melhor posição.
    Premia quem vende bem de forma constante, não só o pico de um lançamento.
    """
    by_appid: Dict[int, TopSeller] = {}
    for ranks in weeks:
        for entry in ranks:
            item = entry.get("item") or {}
            if item.get("type") == DLC_ITEM_TYPE:
                continue
            appid = int(entry["appid"])
            rank = int(entry["rank"])
            seller = by_appid.get(appid)
            if seller is None:
                seller = by_appid[appid] = TopSeller(
                    appid=appid,
                    name=item.get("name") or str(appid),
                    is_free=bool(item.get("is_free")),
                )
            seller.pontos += TOP_SELLERS_PER_WEEK + 1 - rank
            seller.semanas += 1
            seller.melhor_rank = min(seller.melhor_rank, rank)
    return sorted(by_appid.values(), key=lambda s: (-s.pontos, -s.semanas, s.melhor_rank))


def catalog_metadata(seller: TopSeller, data: Dict[str, Any], periodo: Dict[str, Any]) -> Dict[str, Any]:
    """Subconjunto do appdetails + posição no top sellers, guardado em games.raw_metadata."""
    return {
        "fonte": "steam_weekly_top_sellers+appdetails",
        "type": data.get("type"),
        "is_free": data.get("is_free"),
        "developers": data.get("developers") or [],
        "publishers": data.get("publishers") or [],
        "genres": genre_names(data),
        "categories": [c.get("description") for c in data.get("categories") or []],
        "release_date": (data.get("release_date") or {}).get("date"),
        "metacritic": (data.get("metacritic") or {}).get("score"),
        "top_sellers": {
            "pontos": seller.pontos,
            "semanas_no_top100": seller.semanas,
            "melhor_rank": seller.melhor_rank,
            **periodo,
        },
    }
