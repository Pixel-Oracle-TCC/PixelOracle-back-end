"""Validação ABSA: Cohen's Kappa (anotadores) e F1 (Gemini vs gold)."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Sequence, Tuple


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """
    Cohen's Kappa entre dois anotadores.
    labels_a e labels_b devem ter o mesmo comprimento.
    """
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("Listas de rótulos devem ter o mesmo comprimento > 0.")

    n = len(labels_a)
    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    po = agree / n

    cats_a = Counter(labels_a)
    cats_b = Counter(labels_b)
    categories = set(cats_a) | set(cats_b)
    pe = sum((cats_a[c] / n) * (cats_b[c] / n) for c in categories)

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def f1_score(
    y_true: Sequence[str], y_pred: Sequence[str], *, average: str = "macro"
) -> float:
    """F1 multiclasse simples (macro ou micro) sem sklearn dependency no caminho crítico."""
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("y_true e y_pred devem ter o mesmo comprimento > 0.")

    labels = sorted(set(y_true) | set(y_pred))
    if average == "micro":
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        # micro F1 == accuracy em classificação single-label
        return tp / len(y_true)

    f1s: List[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall == 0:
            f1s.append(0.0)
        else:
            f1s.append(2 * precision * recall / (precision + recall))
    return sum(f1s) / len(f1s) if f1s else 0.0


def paired_labels(
    rows: Iterable[dict],
    key_a: str,
    key_b: str,
) -> Tuple[List[str], List[str]]:
    """Extrai pares de rótulos normalizados (lower/strip) de dicts."""
    a_list: List[str] = []
    b_list: List[str] = []
    for row in rows:
        a = row.get(key_a)
        b = row.get(key_b)
        if a is None or b is None:
            continue
        a_list.append(str(a).strip().lower())
        b_list.append(str(b).strip().lower())
    return a_list, b_list
