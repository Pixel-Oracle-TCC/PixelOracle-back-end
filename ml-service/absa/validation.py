"""Validação ABSA: Cohen's Kappa (anotadores) e F1 (Gemini vs gold), multi-aspecto.

Com vários aspectos por review, a comparação é feita em "células" (review × categoria):
cada célula recebe o sentimento anotado ou "ausente". O Kappa usa essas células; o F1
compara os pares (categoria, sentimento) de cada review.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from absa.taxonomy import CATEGORIES, normalize_category, normalize_sentiment

ABSENT = "ausente"
MIXED = "misto"

Annotation = Sequence[Mapping[str, str]]
Pair = Tuple[str, str]


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Cohen's Kappa entre dois anotadores (listas de mesmo comprimento)."""
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("Listas de rótulos devem ter o mesmo comprimento > 0.")

    n = len(labels_a)
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    cats_a = Counter(labels_a)
    cats_b = Counter(labels_b)
    pe = sum((cats_a[c] / n) * (cats_b[c] / n) for c in set(cats_a) | set(cats_b))
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def f1_score(y_true: Sequence[str], y_pred: Sequence[str], *, average: str = "macro") -> float:
    """F1 multiclasse single-label (macro ou micro), sem sklearn no caminho crítico."""
    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("y_true e y_pred devem ter o mesmo comprimento > 0.")
    if average == "micro":
        return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    f1s: List[float] = []
    for label in sorted(set(y_true) | set(y_pred)):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        f1s.append(_f1(tp, fp, fn))
    return sum(f1s) / len(f1s) if f1s else 0.0


def to_pairs(annotation: Iterable[Mapping[str, str]]) -> Set[Pair]:
    return {
        (normalize_category(a.get("categoria", "")), normalize_sentiment(a.get("sentimento", "")))
        for a in annotation
    }


def cell_labels(annotation: Iterable[Mapping[str, str]]) -> Dict[str, str]:
    """categoria → sentimento (ou 'misto' se a review elogia e critica a mesma categoria)."""
    labels: Dict[str, str] = {}
    for categoria, sentimento in to_pairs(annotation):
        labels[categoria] = MIXED if categoria in labels and labels[categoria] != sentimento else sentimento
    return labels


def multilabel_kappa(
    ann_a: Mapping[int, Annotation], ann_b: Mapping[int, Annotation]
) -> Dict[str, float]:
    """
    kappa_celulas: concordância em categoria + sentimento (ausente conta como rótulo).
    kappa_presenca: só se a categoria foi mencionada ou não.
    """
    review_ids = sorted(set(ann_a) & set(ann_b))
    if not review_ids:
        raise ValueError("Nenhuma review anotada pelos dois anotadores.")
    cells_a: List[str] = []
    cells_b: List[str] = []
    for rid in review_ids:
        la, lb = cell_labels(ann_a[rid]), cell_labels(ann_b[rid])
        for categoria in CATEGORIES:
            cells_a.append(la.get(categoria, ABSENT))
            cells_b.append(lb.get(categoria, ABSENT))
    presence_a = ["sim" if x != ABSENT else "nao" for x in cells_a]
    presence_b = ["sim" if x != ABSENT else "nao" for x in cells_b]
    return {
        "reviews": len(review_ids),
        "celulas": len(cells_a),
        "kappa_celulas": round(cohen_kappa(cells_a, cells_b), 4),
        "kappa_presenca": round(cohen_kappa(presence_a, presence_b), 4),
    }


def multilabel_f1(gold: Mapping[int, Annotation], pred: Mapping[int, Annotation]) -> Dict[str, float]:
    """Precisão/recall/F1 sobre pares (categoria, sentimento). Micro + macro por categoria."""
    review_ids = sorted(set(gold) & set(pred))
    if not review_ids:
        raise ValueError("Nenhuma review em comum entre gold e predição.")
    tp = fp = fn = 0
    per_category: Dict[str, List[int]] = {c: [0, 0, 0] for c in CATEGORIES}
    for rid in review_ids:
        g, p = to_pairs(gold[rid]), to_pairs(pred[rid])
        for pair in p & g:
            per_category[pair[0]][0] += 1
        for pair in p - g:
            per_category[pair[0]][1] += 1
        for pair in g - p:
            per_category[pair[0]][2] += 1
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    present = {c: v for c, v in per_category.items() if sum(v) > 0}
    macro = sum(_f1(*v) for v in present.values()) / len(present) if present else 0.0
    return {
        "reviews": len(review_ids),
        "precisao_micro": round(precision, 4),
        "recall_micro": round(recall, 4),
        "f1_micro": round(_f1(tp, fp, fn), 4),
        "f1_macro_categorias": round(macro, 4),
        "f1_por_categoria": {c: round(_f1(*v), 4) for c, v in present.items()},
    }


def parse_annotation(text: str) -> List[Dict[str, str]]:
    """Formato da planilha: 'gameplay:positivo; historia:negativo' ('nenhum' = sem aspectos)."""
    text = (text or "").strip().lower()
    if not text or text in {"nenhum", "-", "n/a"}:
        return []
    result = []
    for chunk in text.replace(",", ";").split(";"):
        if ":" not in chunk:
            continue
        categoria, sentimento = (part.strip() for part in chunk.split(":", 1))
        result.append({"categoria": categoria, "sentimento": sentimento})
    return result


def _f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
