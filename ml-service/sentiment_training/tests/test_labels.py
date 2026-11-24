"""Normalização de rótulos da Tétrade — sem rede."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data import InvalidLabelError, clean_review_text, normalize_label_token  # noqa: E402


def test_aliases() -> None:
    assert normalize_label_token("Positivo") == "POS"
    assert normalize_label_token("  NEGATIVO ") == "NEG"
    assert normalize_label_token("Misto(+)") == "MAJ_POS"
    assert normalize_label_token("Misto (+)") == "MAJ_POS"
    assert normalize_label_token("Misto (=)") == "DIV"
    assert normalize_label_token("Misto") == "DIV"
    assert normalize_label_token("Misto (−)") == "MAJ_NEG"
    assert normalize_label_token("Misto (–)") == "MAJ_NEG"
    assert normalize_label_token("Misto (-)") == "MAJ_NEG"
    assert normalize_label_token("Não mencionado") == "NM"
    assert normalize_label_token("Nao mencionado") == "NM"
    assert normalize_label_token("") is None
    assert normalize_label_token(None) is None


def test_invalid_does_not_guess() -> None:
    try:
        normalize_label_token("Mecânica")
    except InvalidLabelError as exc:
        assert "Mecânica" in str(exc)
    else:
        raise AssertionError("deveria recusar valor fora do mapa")


def test_clean_review_text() -> None:
    assert clean_review_text(None) == ""
    assert clean_review_text(float("nan")) == ""
    assert clean_review_text("  Ótimo\x00jogo \n ver https://steam.com/x  ") == "Ótimo jogo ver"
    assert clean_review_text("<b>legal</b>") == "legal"


if __name__ == "__main__":
    test_aliases()
    test_invalid_does_not_guess()
    test_clean_review_text()
    print("ok test_labels")
