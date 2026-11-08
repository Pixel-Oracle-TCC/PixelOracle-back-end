"""Macro-F1, acurácia, relatório por classe, kappa e matrizes de confusão."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from config import AXES, OUTPUTS_DIR, ORDINAL_EXCLUDE, ORDINAL_ORDER


def macro_f1(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> float:
    return float(f1_score(y_true, y_pred, labels=list(labels), average="macro", zero_division=0))


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    return float(accuracy_score(y_true, y_pred))


def per_class_report(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]
) -> pd.DataFrame:
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(labels), zero_division=0
    )
    return pd.DataFrame(
        {
            "classe": list(labels),
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": support,
        }
    )


def axis_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]
) -> Dict[str, float]:
    report = classification_report(
        y_true, y_pred, labels=list(labels), output_dict=True, zero_division=0
    )
    return {
        "macro_f1": macro_f1(y_true, y_pred, labels),
        "accuracy": accuracy(y_true, y_pred),
        "weighted_f1": float(report.get("weighted avg", {}).get("f1-score", 0.0)),
    }


def kappa_unweighted(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if len(y_true) == 0:
        return float("nan")
    return float(cohen_kappa_score(y_true, y_pred))


def kappa_quadratic_ordinal(y_true: Sequence[str], y_pred: Sequence[str]) -> Optional[float]:
    """Kappa ponderado só no subconjunto ordinal (exclui NM e NEU)."""
    keep_t: List[str] = []
    keep_p: List[str] = []
    allowed = set(ORDINAL_ORDER)
    for t, p in zip(y_true, y_pred):
        if t in ORDINAL_EXCLUDE or p in ORDINAL_EXCLUDE:
            continue
        if t not in allowed or p not in allowed:
            continue
        keep_t.append(t)
        keep_p.append(p)
    if len(keep_t) < 2:
        return None
    return float(
        cohen_kappa_score(
            keep_t,
            keep_p,
            labels=list(ORDINAL_ORDER),
            weights="quadratic",
        )
    )


def save_confusion(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
    stem: str,
) -> Tuple[Path, Path]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    matrix = confusion_matrix(y_true, y_pred, labels=list(labels))
    csv_path = OUTPUTS_DIR / f"{stem}.csv"
    png_path = OUTPUTS_DIR / f"{stem}.png"
    pd.DataFrame(matrix, index=list(labels), columns=list(labels)).to_csv(csv_path)
    fig, ax = plt.subplots(figsize=(7, 6))
    try:
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=list(labels),
            yticklabels=list(labels),
            ax=ax,
        )
        ax.set_xlabel("Predição")
        ax.set_ylabel("Rótulo")
        ax.set_title(stem)
        fig.savefig(png_path, bbox_inches="tight", dpi=120)
    finally:
        plt.close(fig)
    return csv_path, png_path


def mean_std(values: Iterable[float]) -> Tuple[float, float]:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan")
    return float(np.mean(arr)), float(np.std(arr, ddof=0))


def evaluate_multiclass_axes(
    true_by_axis: Mapping[str, Sequence[str]],
    pred_by_axis: Mapping[str, Sequence[str]],
    labels: Sequence[str],
    *,
    stem_prefix: str,
) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    f1s: List[float] = []
    for axis in AXES:
        yt, yp = list(true_by_axis[axis]), list(pred_by_axis[axis])
        m = axis_metrics(yt, yp, labels)
        m["kappa"] = kappa_unweighted(yt, yp)
        qk = kappa_quadratic_ordinal(yt, yp)
        if qk is not None:
            m["kappa_quadratic"] = qk
        save_confusion(yt, yp, labels, f"{stem_prefix}_{axis}")
        per_class_report(yt, yp, labels).to_csv(
            OUTPUTS_DIR / f"{stem_prefix}_{axis}_por_classe.csv", index=False
        )
        summary[axis] = m
        f1s.append(m["macro_f1"])
    summary["_mean"] = {"macro_f1": float(np.mean(f1s)) if f1s else float("nan")}
    return summary
