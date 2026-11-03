"""Prova 7. Ironia e texto curto só entram quando a planilha marca isso."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import AMOSTRA_IDS, ROTULOS, ler_csv, write_json
from ml.experiments import log_experiment

SAIDA = Path(__file__).resolve().parent / "output"


def main() -> None:
    if not ROTULOS.exists():
        curtos = 0
        if AMOSTRA_IDS.exists():
            curtos = sum(1 for row in ler_csv(AMOSTRA_IDS) if int(row["n_palavras"]) <= 40)
        payload = {
            "analisou_modelo": False,
            "motivo": (
                "Não há coluna de flag na planilha, porque a planilha ainda não existe. "
                "Separar ironia e texto curto fica para quando os anotadores marcarem IRONIA."
            ),
            "reviews_de_20_a_40_palavras_na_amostra": curtos,
            "o_que_esse_numero_nao_e": "Não é taxa de erro do modelo. É só o tamanho dos textos já filtrados.",
            "decisao": "sem go",
        }
        write_json(SAIDA / "resultado.json", payload)
        log_experiment("poc_tetrade_robustez", {"analisou_modelo": False, "curtos_20_a_40": curtos})
        print(payload["motivo"])
        return

    linhas = ler_csv(ROTULOS)
    if not linhas or "flags" not in linhas[0]:
        payload = {
            "analisou_modelo": False,
            "motivo": "A planilha não tem a coluna flags. Sem IRONIA marcada não há recorte de robustez.",
            "decisao": "sem go",
        }
    else:
        ironia = [row for row in linhas if "IRONIA" in (row.get("flags") or "")]
        payload = {
            "analisou_modelo": False,
            "reviews_com_flag_ironia": len(ironia),
            "motivo": (
                "A flag existe, mas esta rodada não cruza ironia com previsão de transformer. "
                "O piso da prova 4, se tiver rodado, não é a resposta desta pergunta."
            ),
            "decisao": "sem go",
        }
    write_json(SAIDA / "resultado.json", payload)
    log_experiment("poc_tetrade_robustez", {"analisou_modelo": False})
    print(payload["motivo"])


if __name__ == "__main__":
    main()
