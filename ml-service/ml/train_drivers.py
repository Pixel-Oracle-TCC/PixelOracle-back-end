"""
Treina o RF de drivers de recomendação por gênero (+ um modelo global) e grava em
genre_drivers. Métricas e parâmetros vão para /experiments.

Uso: python ml/train_drivers.py  (depois de cluster_themes.py)
Ver vault: [[Por que Random Forest]] / [[Modelagem e ML]].
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ML_SERVICE_DIR / ".env")

from db.connection import init_engine, session_scope  # noqa: E402
from ml.drivers import DriverResult, build_driver_matrix, train_drivers  # noqa: E402
from ml.experiments import log_experiment  # noqa: E402
from models.orm import Game, Genre, GenreDriver  # noqa: E402
from retrieval.review_repository import game_ids_for_genre, load_scope, load_themes  # noqa: E402


def persist(session, genre_id, result: DriverResult) -> None:
    query = session.query(GenreDriver)
    query = query.filter(GenreDriver.genre_id.is_(None)) if genre_id is None else query.filter(
        GenreDriver.genre_id == genre_id
    )
    query.delete(synchronize_session=False)
    if result.trained:
        for driver in result.drivers:
            session.add(
                GenreDriver(
                    genre_id=genre_id,
                    modelo_f1=result.f1_macro,
                    modelo_roc_auc=result.roc_auc,
                    n_amostras=result.n_amostras,
                    **driver,
                )
            )
    session.commit()


def summarize(nome: str, result: DriverResult) -> dict:
    return {
        "escopo": nome,
        "treinado": result.trained,
        "motivo": result.motivo,
        "n_amostras": result.n_amostras,
        "f1_macro": result.f1_macro,
        "f1_macro_std": result.f1_macro_std,
        "roc_auc": result.roc_auc,
        "roc_auc_std": result.roc_auc_std,
        "top_drivers": [(d["rotulo"], d["importancia"], d["direcao"]) for d in result.drivers[:5]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RF de drivers de recomendação")
    parser.add_argument("--min-support", type=int, default=10)
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    try:
        themes = load_themes(session)
        if not themes:
            raise SystemExit("Nenhum tema encontrado. Rode scripts/cluster_themes.py antes.")

        log = []
        all_game_ids = [g.id for g in session.query(Game.id).all()]
        scopes = [(None, "Todos os gêneros", all_game_ids)]
        scopes += [
            (genre.id, genre.nome, game_ids_for_genre(session, genre.id))
            for genre in session.query(Genre).order_by(Genre.nome).all()
        ]
        for genre_id, nome, game_ids in scopes:
            reviews, aspects = load_scope(session, game_ids)
            matrix = build_driver_matrix(reviews, aspects, themes, min_support=args.min_support)
            result = train_drivers(matrix)
            persist(session, genre_id, result)
            log.append(summarize(nome, result))
            status = (
                f"F1 {result.f1_macro} | ROC-AUC {result.roc_auc}" if result.trained else result.motivo
            )
            print(f"... {nome}: n={result.n_amostras} | {status}")

        path = log_experiment(
            "drivers_rf",
            {
                "parametros": {
                    "min_support": args.min_support,
                    "n_estimators": 300,
                    "min_samples_leaf": 5,
                    "class_weight": "balanced",
                    "cv": "StratifiedKFold(5)",
                    "importancia": "permutation_importance(roc_auc, n_repeats=10, hold-out 25%)",
                },
                "resultados": log,
            },
        )
        print(f"✅ Drivers gravados em genre_drivers | log: {path}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
