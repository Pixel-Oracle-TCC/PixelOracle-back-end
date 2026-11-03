"""Piso sem rede neural: classe mais frequente e TF-IDF com regressão logística.

O C é escolhido por validação cruzada dentro do treino, separando por jogo.
A validação externa e o teste não entram nessa escolha.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

from tetrade.metricas import macro_f1

GRADE_C = (0.1, 1.0, 10.0)


def classe_majoritaria(treino: Sequence[str]) -> str:
    if not treino:
        raise ValueError("Treino vazio.")
    return Counter(treino).most_common(1)[0][0]


def prever_majoritaria(treino: Sequence[str], n: int) -> list[str]:
    classe = classe_majoritaria(treino)
    return [classe] * n


def escolher_c(
    textos: Sequence[str],
    rotulos: Sequence[str],
    grupos: Sequence[int],
) -> float:
    """C com maior macro-F1 médio na validação cruzada por jogo. Empate fica com o menor C."""
    n_grupos = len(set(grupos))
    n_classes = len(set(rotulos))
    if n_grupos < 3 or n_classes < 2 or len(textos) < 30:
        return 1.0
    folds = min(3, n_grupos)
    melhor_c = 1.0
    melhor_nota = -1.0
    for c in GRADE_C:
        notas = []
        divisor = GroupKFold(n_splits=folds)
        for treino_idx, val_idx in divisor.split(textos, rotulos, grupos):
            modelo = _pipeline(c, min_df=1 if len(treino_idx) < 50 else 2)
            modelo.fit([textos[i] for i in treino_idx], [rotulos[i] for i in treino_idx])
            previsto = modelo.predict([textos[i] for i in val_idx])
            classes = sorted(set(rotulos))
            nota = macro_f1([rotulos[i] for i in val_idx], list(previsto), classes)
            if nota is not None:
                notas.append(nota)
        media = sum(notas) / len(notas) if notas else -1.0
        if media > melhor_nota:
            melhor_nota = media
            melhor_c = c
    return melhor_c


def treinar(textos: Sequence[str], rotulos: Sequence[str], c: float):
    if len(set(rotulos)) < 2:
        return None
    modelo = _pipeline(c, min_df=1 if len(textos) < 50 else 2)
    modelo.fit(list(textos), list(rotulos))
    return modelo


def _pipeline(c: float, min_df: int) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=min_df,
                    max_features=20000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=c,
                    class_weight="balanced",
                    max_iter=1000,
                    solver="lbfgs",
                ),
            ),
        ]
    )
