"""Prova 5. O script do transformer existe e não treina nesta etapa."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import ROTULOS, write_json
from ml.experiments import log_experiment
from tetrade.criterios import CRITERIOS

SAIDA = Path(__file__).resolve().parent / "output"


def main() -> None:
    pedido = os.getenv("TETRADE_TREINAR") == "1"
    payload = {
        "treinou": False,
        "modelos_planejados": ["BERTimbau base", "XLM-RoBERTa base"],
        "sementes_planejadas": [13, 42, 2024],
        "hiperparametros_planejados": {
            "otimizador": "AdamW",
            "taxa_de_aprendizado": 2e-5,
            "batch": 16,
            "epocas_maximas": 10,
            "paciencia": 3,
            "tokens_maximos": 256,
            "cabecas": 4,
            "perda": "ponderada por classe",
        },
        "pedido_explicito": pedido,
        "planilha_presente": ROTULOS.exists(),
        "motivo": (
            "Esta etapa não treina transformer. Falta a planilha humana de cerca de 500 reviews, "
            "falta GPU reservada, e baixar BERTimbau agora não responde a pergunta da prova. "
            "O comando futuro é TETRADE_TREINAR=1, com as dependências de poc/tetrade/requirements-treino.txt, "
            "e mesmo assim o teste humano só entra uma vez, no fim."
        ),
        "criterios_fixados_antes": CRITERIOS,
        "decisao": "sem go",
        "o_que_isto_nao_e": "Não é uma comparação entre BERTimbau e TF-IDF.",
    }
    write_json(SAIDA / "resultado.json", payload)
    log_experiment("poc_tetrade_transformer", {"treinou": False})
    print(payload["motivo"])


if __name__ == "__main__":
    main()
