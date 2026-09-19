"""Testes unitários sintéticos — ABSA validation + triangulação (sem rede)."""

from __future__ import annotations

import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))

from absa.validation import cohen_kappa, f1_score  # noqa: E402
from triangulation.engine import TriangulationEngine  # noqa: E402


def test_cohen_kappa_perfect() -> None:
    a = ["gameplay", "historia", "preco"]
    b = ["gameplay", "historia", "preco"]
    assert cohen_kappa(a, b) == 1.0


def test_f1_macro() -> None:
    y_true = ["positivo", "negativo", "positivo"]
    y_pred = ["positivo", "negativo", "negativo"]
    score = f1_score(y_true, y_pred, average="macro")
    assert 0.0 < score < 1.0


def test_triangulation_engine_structure() -> None:
    engine = TriangulationEngine()
    result = engine.build(
        pitch={"titulo": "Test", "descricao": "Um jogo de teste", "price_brl": 29.9, "genres": ["Indie"]},
        prediction={
            "previsao_pixel_oracle": {
                "risco_comercial": "Médio Risco",
                "chance_sucesso_estimada_pct": 40.0,
            }
        },
        similar_games=[
            {"titulo": "Ref A", "similaridade": 0.8, "preco_brl": 40.0}
        ],
        genre_insights=[
            {
                "aspecto": "gameplay",
                "frequencia_positiva": 10,
                "frequencia_negativa": 2,
                "significancia": 0.01,
                "significativo": True,
            },
            {
                "aspecto": "performance",
                "frequencia_positiva": 1,
                "frequencia_negativa": 8,
                "significancia": 0.02,
                "significativo": True,
            },
        ],
    )
    dash = result["dashboard"]
    assert "pontos_fortes" in dash
    assert "pontos_fracos" in dash
    assert "oportunidades" in dash
    assert "riscos" in dash
    assert len(dash["jogos_similares"]) == 1
    assert len(dash["pontos_fortes"]) >= 1


if __name__ == "__main__":
    test_cohen_kappa_perfect()
    test_f1_macro()
    test_triangulation_engine_structure()
    print("✅ testes sintéticos OK")
