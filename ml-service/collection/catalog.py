"""Regras do catálogo de jogos: o que entra, com quais gêneros e metadados.

Escopo: dados de jogo (top sellers + appdetails da Steam), nunca de usuário.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

_MONTHS_PT = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}
_MONTHS_EN = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
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


def category_pairs(data: Dict[str, Any]) -> List[Tuple[int, str]]:
    """Lista (steam_category_id, nome) das categorias do appdetails."""
    pairs: List[Tuple[int, str]] = []
    seen: set[int] = set()
    for cat in data.get("categories") or []:
        try:
            cid = int(cat["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if cid in seen:
            continue
        nome = (cat.get("description") or "").strip() or str(cid)
        pairs.append((cid, nome))
        seen.add(cid)
    return pairs


def name_list(data: Dict[str, Any], key: str) -> List[str]:
    raw = data.get(key) or []
    if not isinstance(raw, list):
        return []
    names: List[str] = []
    for item in raw:
        nome = str(item).strip()
        if nome and nome not in names:
            names.append(nome)
    return names


def parse_release_date(data: Dict[str, Any]) -> Optional[date]:
    """Parseia release_date.date da Store (pt: 24/fev./2022 ou en: Feb 24, 2022)."""
    date_str = ((data.get("release_date") or {}).get("date") or "").strip()
    if not date_str:
        return None
    # 24/fev./2022 | 24 fev 2022 | 24 Feb, 2022
    m = re.search(
        r"(?P<d>\d{1,2})\s*[/\s]\s*(?P<mon>[A-Za-zçÇ.]{3,})\s*[/\s,]+\s*(?P<y>20\d{2})",
        date_str,
        flags=re.IGNORECASE,
    )
    if m:
        mon = m.group("mon").lower().replace(".", "")[:3]
        month = _MONTHS_PT.get(mon) or _MONTHS_EN.get(mon)
        if month:
            try:
                return date(int(m.group("y")), month, int(m.group("d")))
            except ValueError:
                return None
    # Feb 24, 2022
    m = re.search(
        r"(?P<mon>[A-Za-z]{3,})\s+(?P<d>\d{1,2}),?\s+(?P<y>20\d{2})",
        date_str,
        flags=re.IGNORECASE,
    )
    if m:
        mon = m.group("mon").lower()[:3]
        month = _MONTHS_EN.get(mon) or _MONTHS_PT.get(mon)
        if month:
            try:
                return date(int(m.group("y")), month, int(m.group("d")))
            except ValueError:
                return None
    # só o ano
    years = re.findall(r"20\d{2}", date_str)
    if years:
        try:
            return date(int(years[-1]), 1, 1)
        except ValueError:
            return None
    return None


def parse_supported_languages(data: Dict[str, Any]) -> List[str]:
    """Remove HTML e '*' (áudio) da string supported_languages da Store."""
    raw = data.get("supported_languages") or ""
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = re.sub(r"<[^>]+>", ",", str(raw))
    names: List[str] = []
    for part in text.split(","):
        nome = part.replace("*", "").strip()
        if nome and nome not in names:
            names.append(nome)
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
