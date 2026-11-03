"""Métricas básicas com dados sintéticos."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import accuracy, kappa_unweighted, macro_f1  # noqa: E402


def test_perfect_scores() -> None:
    y = ["POS", "NEG", "NM", "POS"]
    assert macro_f1(y, y, ["POS", "NEG", "NM"]) == 1.0
    assert accuracy(y, y) == 1.0
    assert kappa_unweighted(y, y) == 1.0


def test_macro_f1_handles_missing_class() -> None:
    y_true = ["POS", "POS", "NEG"]
    y_pred = ["POS", "NEG", "NEG"]
    score = macro_f1(y_true, y_pred, ["POS", "NEG", "NM"])
    assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    test_perfect_scores()
    test_macro_f1_handles_missing_class()
    print("ok test_metrics")
