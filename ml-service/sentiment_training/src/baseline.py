"""Baseline: TF-IDF palavra+char concatenado e LogisticRegression por eixo."""

from __future__ import annotations

import logging
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from config import (
    AXES,
    BINARY_MARKERS,
    CLASSES_5,
    CLASSES_7,
    LOGREG_C_GRID,
    TEXT_COL,
    TFIDF_CHAR_MAX_FEATURES,
    TFIDF_WORD_MAX_FEATURES,
    map_scheme_label,
)
from metrics import evaluate_multiclass_axes, macro_f1

logger = logging.getLogger(__name__)


def _texts(frame: pd.DataFrame) -> List[str]:
    return frame[TEXT_COL].astype(str).tolist()


def _labels(frame: pd.DataFrame, axis: str, scheme: str) -> List[str]:
    if scheme == "binary":
        raise ValueError("use binary helpers")
    return [map_scheme_label(str(v), scheme) for v in frame[axis].tolist()]


def _binary_targets(series: pd.Series) -> Dict[str, np.ndarray]:
    values = series.astype(str).tolist()
    mencionado = np.array([c != "NM" for c in values], dtype=int)
    elogio = np.array([c in {"POS", "MAJ_POS", "DIV", "MAJ_NEG"} for c in values], dtype=int)
    critica = np.array([c in {"NEG", "MAJ_POS", "DIV", "MAJ_NEG"} for c in values], dtype=int)
    return {"mencionado": mencionado, "elogio": elogio, "critica": critica}


class TfidfBundle:
    def __init__(self) -> None:
        self.word = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            min_df=2,
            max_features=TFIDF_WORD_MAX_FEATURES,
        )
        self.char = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            sublinear_tf=True,
            lowercase=True,
            min_df=2,
            max_features=TFIDF_CHAR_MAX_FEATURES,
        )

    def fit_transform(self, texts: Sequence[str]):
        return hstack([self.word.fit_transform(texts), self.char.fit_transform(texts)]).tocsr()

    def transform(self, texts: Sequence[str]):
        return hstack([self.word.transform(texts), self.char.transform(texts)]).tocsr()


def train_baseline(
    train: pd.DataFrame,
    val: pd.DataFrame,
    *,
    scheme: str = "7",
    refit_on: pd.DataFrame | None = None,
) -> Tuple[TfidfBundle, Dict[str, object]]:
    bundle = TfidfBundle()
    x_train = bundle.fit_transform(_texts(train))
    x_val = bundle.transform(_texts(val)) if len(val) else None
    models: Dict[str, object] = {}
    best_cs: Dict[str, float] = {}

    if scheme == "binary":
        for axis in AXES:
            targets_tr = _binary_targets(train[axis])
            targets_va = _binary_targets(val[axis])
            for marker in BINARY_MARKERS:
                best_c, best_f1 = 1.0, -1.0
                y_tr, y_va = targets_tr[marker], targets_va[marker]
                for c in LOGREG_C_GRID:
                    clf = LogisticRegression(
                        class_weight="balanced", max_iter=2000, C=c, solver="lbfgs"
                    )
                    clf.fit(x_train, y_tr)
                    if x_val is None:
                        score = 0.0
                    else:
                        pred = clf.predict(x_val)
                        score = macro_f1(
                            [str(v) for v in y_va], [str(v) for v in pred], labels=["0", "1"]
                        )
                    if score > best_f1:
                        best_f1, best_c = score, c
                best_cs[f"{axis}:{marker}"] = best_c
                logger.info("baseline %s/%s C=%.2f val-macroF1=%.3f", axis, marker, best_c, best_f1)
    else:
        labels = list(CLASSES_7 if scheme == "7" else CLASSES_5)
        for axis in AXES:
            y_tr = _labels(train, axis, scheme)
            y_va = _labels(val, axis, scheme)
            best_c, best_f1 = 1.0, -1.0
            for c in LOGREG_C_GRID:
                clf = LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    C=c,
                    solver="lbfgs",
                )
                clf.fit(x_train, y_tr)
                if x_val is None:
                    score = 0.0
                else:
                    pred = clf.predict(x_val)
                    score = macro_f1(y_va, pred.tolist(), labels)
                if score > best_f1:
                    best_f1, best_c = score, c
            best_cs[axis] = best_c
            logger.info("baseline %s C=%.2f val-macroF1=%.3f", axis, best_c, best_f1)

    pool = refit_on if refit_on is not None else train
    if refit_on is not None:
        bundle = TfidfBundle()
        x_pool = bundle.fit_transform(_texts(pool))
    else:
        x_pool = x_train
        pool = train

    if scheme == "binary":
        for axis in AXES:
            targets = _binary_targets(pool[axis])
            for marker in BINARY_MARKERS:
                clf = LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    C=best_cs[f"{axis}:{marker}"],
                    solver="lbfgs",
                )
                clf.fit(x_pool, targets[marker])
                models[f"{axis}:{marker}"] = clf
        return bundle, models

    labels = list(CLASSES_7 if scheme == "7" else CLASSES_5)
    for axis in AXES:
        clf = LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            C=best_cs[axis],
            solver="lbfgs",
        )
        clf.fit(x_pool, _labels(pool, axis, scheme))
        models[axis] = clf
    return bundle, models


def predict_baseline(
    bundle: TfidfBundle,
    models: Dict[str, object],
    frame: pd.DataFrame,
    *,
    scheme: str,
) -> Dict[str, List[str]]:
    x = bundle.transform(_texts(frame))
    if scheme == "binary":
        out: Dict[str, List[str]] = {}
        for axis in AXES:
            for marker in BINARY_MARKERS:
                clf: LogisticRegression = models[f"{axis}:{marker}"]  # type: ignore[assignment]
                out[f"{axis}:{marker}"] = [str(v) for v in clf.predict(x)]
        return out
    return {axis: models[axis].predict(x).tolist() for axis in AXES}  # type: ignore[union-attr]


def evaluate_baseline(
    bundle: TfidfBundle,
    models: Dict[str, object],
    test: pd.DataFrame,
    *,
    scheme: str,
    stem_prefix: str,
) -> Dict[str, Dict[str, float]]:
    preds = predict_baseline(bundle, models, test, scheme=scheme)
    if scheme == "binary":
        from sklearn.metrics import f1_score

        summary: Dict[str, Dict[str, float]] = {}
        for axis in AXES:
            gold = _binary_targets(test[axis])
            axis_scores: Dict[str, float] = {}
            for marker in BINARY_MARKERS:
                y = gold[marker]
                p = np.array(preds[f"{axis}:{marker}"], dtype=int)
                axis_scores[marker] = float(f1_score(y, p, zero_division=0))
            axis_scores["macro_f1"] = float(np.mean(list(axis_scores.values())))
            summary[axis] = axis_scores
        summary["_mean"] = {
            "macro_f1": float(np.mean([summary[a]["macro_f1"] for a in AXES]))
        }
        return summary
    labels = list(CLASSES_7 if scheme == "7" else CLASSES_5)
    true_by = {axis: _labels(test, axis, scheme) for axis in AXES}
    return evaluate_multiclass_axes(true_by, preds, labels, stem_prefix=stem_prefix)
