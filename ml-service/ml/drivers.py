"""Random Forest de drivers de recomendação (key driver analysis).

Pergunta respondida: dentro de um gênero, quais temas (elogios/reclamações) mais pesam
para a review recomendar ou não o jogo?

- y = voted_up da própria review (rótulo REAL da Steam — ao contrário das vendas estimadas
  do modelo descartado, ver legacy/sales_score).
- X = presença de cada tema na review + contexto (faixa de horas jogadas, early access).
- A importância vem de permutation_importance no hold-out (ROC-AUC), não do
  feature_importances_ por impureza, que favorece features com muitos valores.

É um modelo EXPLICATIVO, não preditivo de futuro: os temas saem do próprio texto da
review, então a métrica mede quanto do veredito os temas extraídos explicam.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

PLAYTIME_BUCKETS = (
    ("contexto:menos_2h", 0, 120, "Jogou menos de 2h ao avaliar"),
    ("contexto:2_a_10h", 120, 600, "Jogou de 2h a 10h ao avaliar"),
    ("contexto:10_a_50h", 600, 3000, "Jogou de 10h a 50h ao avaliar"),
    ("contexto:mais_50h", 3000, None, "Jogou mais de 50h ao avaliar"),
)
EARLY_ACCESS_FEATURE = ("contexto:early_access", "Avaliado durante o early access")

MIN_SAMPLES = 150
MIN_MINORITY = 20


@dataclass
class DriverMatrix:
    X: pd.DataFrame
    y: pd.Series
    labels: Dict[str, tuple[str, str]] = field(default_factory=dict)  # feature -> (rotulo, tipo)


@dataclass
class DriverResult:
    trained: bool
    motivo: Optional[str] = None
    n_amostras: int = 0
    f1_macro: Optional[float] = None
    f1_macro_std: Optional[float] = None
    roc_auc: Optional[float] = None
    roc_auc_std: Optional[float] = None
    drivers: List[Dict[str, Any]] = field(default_factory=list)


def build_driver_matrix(
    reviews: Sequence[Mapping[str, Any]],
    aspects: Sequence[Mapping[str, Any]],
    themes: Mapping[int, Mapping[str, Any]],
    *,
    min_support: int = 10,
) -> DriverMatrix:
    review_themes: Dict[int, set] = defaultdict(set)
    for aspect in aspects:
        if aspect.get("theme_id") in themes:
            review_themes[aspect["review_id"]].add(aspect["theme_id"])

    support: Dict[int, int] = defaultdict(int)
    for theme_ids in review_themes.values():
        for theme_id in theme_ids:
            support[theme_id] += 1
    kept = sorted(t for t, n in support.items() if n >= min_support)

    labels: Dict[str, tuple[str, str]] = {}
    for theme_id in kept:
        meta = themes[theme_id]
        prefix = "Elogio" if meta.get("polaridade") == "positivo" else "Reclamação"
        labels[f"tema:{theme_id}"] = (f"{prefix}: {meta.get('rotulo')}", "tema")
    for name, _, _, rotulo in PLAYTIME_BUCKETS:
        labels[name] = (rotulo, "contexto")
    labels[EARLY_ACCESS_FEATURE[0]] = (EARLY_ACCESS_FEATURE[1], "contexto")

    rows = []
    targets = []
    for review in reviews:
        if review.get("recomendada") is None:
            continue
        present = review_themes.get(review["review_id"], set())
        row = {f"tema:{t}": int(t in present) for t in kept}
        minutes = review.get("playtime_at_review") or 0
        for name, low, high, _ in PLAYTIME_BUCKETS:
            row[name] = int(minutes >= low and (high is None or minutes < high))
        row[EARLY_ACCESS_FEATURE[0]] = int(bool(review.get("early_access")))
        rows.append(row)
        targets.append(int(bool(review["recomendada"])))

    X = pd.DataFrame(rows, columns=list(labels.keys())).fillna(0).astype(int)
    return DriverMatrix(X=X, y=pd.Series(targets, name="recomendada"), labels=labels)


def build_classifier(random_state: int = 42) -> RandomForestClassifier:
    # min_samples_leaf alto: features binárias esparsas → folhas minúsculas = overfitting
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )


def train_drivers(matrix: DriverMatrix, *, random_state: int = 42, top_n: int = 15) -> DriverResult:
    X, y = matrix.X, matrix.y
    n = len(y)
    minority = int(min(y.sum(), n - y.sum())) if n else 0
    if n < MIN_SAMPLES or minority < MIN_MINORITY:
        return DriverResult(
            trained=False,
            n_amostras=n,
            motivo=f"amostra insuficiente (n={n}, classe minoritária={minority})",
        )
    theme_cols = [c for c in X.columns if c.startswith("tema:")]
    if not theme_cols:
        return DriverResult(trained=False, n_amostras=n, motivo="nenhum tema com suporte mínimo")

    clf = build_classifier(random_state)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    scores = cross_validate(clf, X, y, cv=cv, scoring=("f1_macro", "roc_auc"))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=random_state
    )
    clf.fit(X_train, y_train)
    perm = permutation_importance(
        clf, X_test, y_test, scoring="roc_auc", n_repeats=10, random_state=random_state, n_jobs=-1
    )

    drivers: List[Dict[str, Any]] = []
    for idx, feature in enumerate(X.columns):
        importance = float(perm.importances_mean[idx])
        if importance <= 0:
            continue
        mask = X[feature] == 1
        suporte = int(mask.sum())
        if suporte == 0:
            continue
        rate_with = float(y[mask].mean())
        rate_without = float(y[~mask].mean()) if (~mask).any() else float("nan")
        rotulo, tipo = matrix.labels[feature]
        drivers.append(
            {
                "feature": feature,
                "rotulo": rotulo,
                "tipo": tipo,
                "importancia": round(importance, 5),
                "importancia_std": round(float(perm.importances_std[idx]), 5),
                "direcao": "aumenta" if rate_with >= rate_without else "reduz",
                "taxa_recomendacao_com": round(rate_with, 4),
                "taxa_recomendacao_sem": None if np.isnan(rate_without) else round(rate_without, 4),
                "suporte": suporte,
            }
        )
    drivers.sort(key=lambda d: -d["importancia"])

    return DriverResult(
        trained=True,
        n_amostras=n,
        f1_macro=round(float(scores["test_f1_macro"].mean()), 4),
        f1_macro_std=round(float(scores["test_f1_macro"].std()), 4),
        roc_auc=round(float(scores["test_roc_auc"].mean()), 4),
        roc_auc_std=round(float(scores["test_roc_auc"].std()), 4),
        drivers=drivers[:top_n],
    )
