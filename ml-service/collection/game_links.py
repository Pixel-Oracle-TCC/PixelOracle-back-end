"""Helpers para vincular gêneros, categorias, estúdios e idiomas a um jogo.

Só dados de jogo — sem identificação de usuário.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from sqlalchemy.orm import Session

from collection.catalog import (
    category_pairs,
    genre_names,
    name_list,
    parse_supported_languages,
)
from models.orm import (
    Category,
    Developer,
    GameCategory,
    GameDeveloper,
    GameGenre,
    GameLanguage,
    GamePublisher,
    Genre,
    Language,
    Publisher,
)


def _link_named(
    session: Session,
    *,
    game_id: int,
    names: List[str],
    entity_cls: Type[Any],
    link_cls: Type[Any],
    fk_name: str,
) -> None:
    for nome in names:
        entity = session.query(entity_cls).filter_by(nome=nome).one_or_none()
        if entity is None:
            entity = entity_cls(nome=nome)
            session.add(entity)
            session.flush()
        link_kwargs = {"game_id": game_id, fk_name: entity.id}
        exists = session.query(link_cls).filter_by(**link_kwargs).one_or_none()
        if exists is None:
            session.add(link_cls(**link_kwargs))


def link_genres(session: Session, game_id: int, names: List[str]) -> None:
    _link_named(
        session,
        game_id=game_id,
        names=names,
        entity_cls=Genre,
        link_cls=GameGenre,
        fk_name="genre_id",
    )


def link_categories(session: Session, game_id: int, pairs: List[tuple[int, str]]) -> None:
    for steam_id, nome in pairs:
        cat = session.query(Category).filter_by(steam_category_id=steam_id).one_or_none()
        if cat is None:
            cat = Category(steam_category_id=steam_id, nome=nome)
            session.add(cat)
            session.flush()
        elif cat.nome != nome:
            cat.nome = nome
        exists = (
            session.query(GameCategory)
            .filter_by(game_id=game_id, category_id=cat.id)
            .one_or_none()
        )
        if exists is None:
            session.add(GameCategory(game_id=game_id, category_id=cat.id))


def link_from_appdetails(session: Session, game_id: int, data: Dict[str, Any]) -> None:
    """Preenche vínculos N:N a partir do bloco data do appdetails."""
    link_genres(session, game_id, genre_names(data))
    link_categories(session, game_id, category_pairs(data))
    _link_named(
        session,
        game_id=game_id,
        names=name_list(data, "developers"),
        entity_cls=Developer,
        link_cls=GameDeveloper,
        fk_name="developer_id",
    )
    _link_named(
        session,
        game_id=game_id,
        names=name_list(data, "publishers"),
        entity_cls=Publisher,
        link_cls=GamePublisher,
        fk_name="publisher_id",
    )
    _link_named(
        session,
        game_id=game_id,
        names=parse_supported_languages(data),
        entity_cls=Language,
        link_cls=GameLanguage,
        fk_name="language_id",
    )
