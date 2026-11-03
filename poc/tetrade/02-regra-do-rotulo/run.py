"""Prova 2. A contagem do manual reproduz os 13 exemplos."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import write_json
from ml.experiments import log_experiment
from tetrade.rotulo import conferir_exemplos, para_binario, para_cinco

SAIDA = Path(__file__).resolve().parent / "output"
FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "ml-service"
    / "tetrade"
    / "fixtures"
    / "exemplos_manual.json"
)


def main() -> None:
    exemplos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    falhas = conferir_exemplos(exemplos)
    cinco = []
    for exemplo in exemplos:
        for eixo, bloco in exemplo["eixos"].items():
            cinco.append(
                {
                    "id": exemplo["id"],
                    "eixo": eixo,
                    "sete": bloco["rotulo"],
                    "cinco": para_cinco(bloco["rotulo"]),
                    "binario": para_binario(bloco["rotulo"]),
                }
            )
    payload = {
        "hipotese": "A contagem escrita no manual produz o rótulo dos 13 exemplos.",
        "o_que_isto_nao_e": "Não é um modelo e não mede se duas pessoas anotam igual.",
        "exemplos": len(exemplos),
        "falhas": falhas,
        "passou": not falhas,
        "esquema_de_cinco_nos_exemplos": cinco,
        "nota": "A função não lê o texto. A pessoa lista os aspectos; a função só aplica a tabela de contagem.",
    }
    write_json(SAIDA / "resultado.json", payload)
    log_experiment("poc_tetrade_rotulo", {"passou": payload["passou"], "exemplos": len(exemplos)})
    print(f"exemplos: {len(exemplos)} | falhas: {len(falhas)}")
    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
