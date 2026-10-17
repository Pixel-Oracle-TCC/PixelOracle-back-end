"""Leitura de reviews, aspectos e temas do Postgres no formato das funções puras.

Nenhuma consulta aqui seleciona dado de autor — o schema nem tem essas colunas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from absa.significance import quote_rank_key
from collection.reviews_client import FATIA_PROPORCIONAL, FATIAS_UTEIS
from models.orm import Game, GameGenre, Genre, GenreDriver, Review, ReviewAspect, Theme, ThemeStat

MAX_REVIEW_TEXT = 600
MAX_DEV_RESPONSE = 600


def load_themes(session: Session) -> Dict[int, Dict[str, Any]]:
    return {
        t.id: {"rotulo": t.rotulo, "categoria": t.categoria, "polaridade": t.polaridade}
        for t in session.query(Theme).all()
    }


def load_scope(
    session: Session,
    game_ids: Sequence[int],
    *,
    only_proportional: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Reviews já processadas pela ABSA + aspectos.

    Por padrão só a fatia `proporcional` (métricas / RF sem viés 50/50 das úteis).
    Jogos com elegivel_metricas=FALSE ficam de fora.
    """
    if not game_ids:
        return [], []
    where = [
        Review.game_id.in_(list(game_ids)),
        Review.absa_processed_at.isnot(None),
        Game.elegivel_metricas.is_(True),
    ]
    if only_proportional:
        where.append(Review.fatias.contains([FATIA_PROPORCIONAL]))
    review_rows = session.execute(
        select(
            Review.id,
            Review.game_id,
            Game.titulo,
            Review.recomendada,
            Review.votos_uteis,
            Review.votes_funny,
            Review.weighted_vote_score,
            Review.playtime_at_review,
            Review.early_access,
        )
        .join(Game, Game.id == Review.game_id)
        .where(*where)
    ).all()
    reviews = [
        {
            "review_id": r.id,
            "game_id": r.game_id,
            "game_titulo": r.titulo,
            "recomendada": r.recomendada,
            "votos_uteis": r.votos_uteis,
            "votes_funny": r.votes_funny,
            "weighted_vote_score": float(r.weighted_vote_score) if r.weighted_vote_score is not None else None,
            "playtime_at_review": r.playtime_at_review,
            "early_access": r.early_access,
        }
        for r in review_rows
    ]
    review_ids = [r["review_id"] for r in reviews]
    if not review_ids:
        return reviews, []
    aspect_rows = session.execute(
        select(
            ReviewAspect.review_id,
            ReviewAspect.theme_id,
            ReviewAspect.trecho,
            ReviewAspect.trecho_literal,
        ).where(ReviewAspect.review_id.in_(review_ids), ReviewAspect.theme_id.isnot(None))
    ).all()
    aspects = [
        {
            "review_id": a.review_id,
            "theme_id": a.theme_id,
            "trecho": a.trecho,
            "trecho_literal": a.trecho_literal,
        }
        for a in aspect_rows
    ]
    return reviews, aspects


def find_genres(session: Session, names: Sequence[str]) -> List[Genre]:
    normalized = [n.strip().lower() for n in names if n and str(n).strip()]
    if not normalized:
        return []
    return session.query(Genre).filter(func.lower(Genre.nome).in_(normalized)).all()


def game_ids_for_genre(session: Session, genre_id: int) -> List[int]:
    rows = session.execute(select(GameGenre.game_id).where(GameGenre.genre_id == genre_id)).all()
    return [r.game_id for r in rows]


def load_genre_theme_stats(session: Session, genre_ids: Sequence[int]) -> List[Dict[str, Any]]:
    if not genre_ids:
        return []
    rows = (
        session.query(ThemeStat, Theme, Genre.nome)
        .join(Theme, Theme.id == ThemeStat.theme_id)
        .join(Genre, Genre.id == ThemeStat.genre_id)
        .filter(ThemeStat.genre_id.in_(list(genre_ids)))
        .all()
    )
    result = []
    for stat, theme, genre_nome in rows:
        result.append(
            {
                "genero": genre_nome,
                "theme_id": theme.id,
                "rotulo": theme.rotulo,
                "categoria": theme.categoria,
                "polaridade": theme.polaridade,
                "reviews_com_tema": stat.reviews_com_tema,
                "total_reviews": stat.total_reviews,
                "prevalencia": _f(stat.prevalencia),
                "wilson_low": _f(stat.wilson_low),
                "wilson_high": _f(stat.wilson_high),
                "jogos_distintos": stat.jogos_distintos,
                "total_jogos": stat.total_jogos,
                "votos_uteis": stat.votos_uteis,
                "pct_recomendadas_com_tema": _f(stat.pct_recomendadas_com_tema),
                "p_value": _f(stat.p_value),
                "p_value_ajustado": _f(stat.p_value_ajustado),
                "log_odds": _f(stat.log_odds),
                "significativo": bool(stat.significativo),
                "jogos_exemplo": stat.jogos_exemplo or [],
                "citacoes": stat.citacoes or [],
                "contexto": stat.contexto or {},
            }
        )
    return result


def load_drivers(
    session: Session, genre_ids: Sequence[int], *, top_n: int = 6
) -> List[Dict[str, Any]]:
    """Drivers dos gêneros do pitch; sem modelo por gênero, usa o global (genre_id NULL)."""
    query = session.query(GenreDriver, Genre.nome).outerjoin(Genre, Genre.id == GenreDriver.genre_id)
    rows = query.filter(GenreDriver.genre_id.in_(list(genre_ids))).all() if genre_ids else []
    escopo = "genero"
    if not rows:
        rows = query.filter(GenreDriver.genre_id.is_(None)).all()
        escopo = "global"
    drivers = [
        {
            "genero": genre_nome or "Todos os gêneros",
            "escopo": escopo,
            "feature": d.feature,
            "rotulo": d.rotulo,
            "tipo": d.tipo,
            "importancia": _f(d.importancia),
            "importancia_std": _f(d.importancia_std),
            "direcao": d.direcao,
            "taxa_recomendacao_com": _f(d.taxa_recomendacao_com),
            "taxa_recomendacao_sem": _f(d.taxa_recomendacao_sem),
            "suporte": d.suporte,
            "modelo": {"f1_macro": _f(d.modelo_f1), "roc_auc": _f(d.modelo_roc_auc), "n_amostras": d.n_amostras},
        }
        for d, genre_nome in rows
    ]
    drivers.sort(key=lambda d: -(d["importancia"] or 0))
    return drivers[:top_n]


def top_reviews_for_game(session: Session, game_id: int, *, per_polarity: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """Reviews de referência: preferem fatias úteis (citações), não a proporcional."""
    rows = (
        session.query(Review)
        .filter(Review.game_id == game_id, Review.texto.isnot(None))
        .all()
    )

    def _as_dict(r: Review) -> Dict[str, Any]:
        return {
            "review_id": r.id,
            "recomendada": bool(r.recomendada),
            "texto": (r.texto or "")[:MAX_REVIEW_TEXT],
            "votos_uteis": r.votos_uteis or 0,
            "votes_funny": r.votes_funny or 0,
            "weighted_vote_score": _f(r.weighted_vote_score),
            "horas_jogadas": round((r.playtime_at_review or 0) / 60, 1),
            "idioma": r.language,
            "early_access": bool(r.early_access),
            "resposta_desenvolvedor": (r.developer_response or "")[:MAX_DEV_RESPONSE] or None,
            "fatias": list(r.fatias or []),
        }

    useful = [_as_dict(r) for r in rows if FATIAS_UTEIS.intersection(r.fatias or [])]
    pool = useful or [_as_dict(r) for r in rows]
    positives = sorted((r for r in pool if r["recomendada"]), key=quote_rank_key)[:per_polarity]
    negatives = sorted((r for r in pool if not r["recomendada"]), key=quote_rank_key)[:per_polarity]
    return {"positivas": positives, "negativas": negatives}


def _f(value: Optional[Any]) -> Optional[float]:
    return float(value) if value is not None else None
