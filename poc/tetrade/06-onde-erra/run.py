"""Prova 6. Onde o piso acerta e onde falha, só se a prova 4 tiver treinado."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _comum import PREDICOES, gravar_csv, ler_csv, ler_json, write_json
from ml.experiments import log_experiment
from tetrade.criterios import CRITERIOS
from tetrade.metricas import f1_por_classe, matriz
from tetrade.rotulo import CINCO_CLASSES, EIXOS

SAIDA = Path(__file__).resolve().parent / "output"
PISO = Path(__file__).resolve().parents[1] / "04-piso-sem-rede" / "output" / "resultado.json"


def main() -> None:
    if not PISO.exists() or not ler_json(PISO).get("treinou"):
        payload = {
            "gerou": False,
            "motivo": "A prova 4 não treinou. Sem previsão não há matriz de confusão.",
            "decisao": "sem go",
        }
        write_json(SAIDA / "resultado.json", payload)
        log_experiment("poc_tetrade_erros", {"gerou": False})
        print(payload["motivo"])
        return

    linhas = ler_csv(PREDICOES)
    blocos = {}
    linhas_csv = []
    for eixo in EIXOS:
        do_eixo = [row for row in linhas if row["eixo"] == eixo]
        verdade = [row["verdade"] for row in do_eixo]
        previsto = [row["previsto_tfidf"] for row in do_eixo]
        por_classe = f1_por_classe(verdade, previsto, CINCO_CLASSES)
        blocos[eixo] = {
            "matriz": matriz(verdade, previsto, CINCO_CLASSES),
            "classes": list(CINCO_CLASSES),
            "f1_por_classe": por_classe,
            "classes_sem_conclusao": [
                classe for classe, info in por_classe.items() if not info["conclusao"]
            ],
        }
        for classe, info in por_classe.items():
            linhas_csv.append({"eixo": eixo, "classe": classe, **info})
        _png(eixo, blocos[eixo]["matriz"])
    payload = {
        "gerou": True,
        "leitura": "Na matriz, a linha é o rótulo humano e a coluna é a previsão do TF-IDF.",
        "minimo_para_concluir": CRITERIOS["minimo_de_exemplos_para_concluir_sobre_uma_classe"],
        "eixos": blocos,
        "decisao": "sem go",
        "o_que_isto_nao_e": "Uma classe com menos de 30 exemplos não sustenta conclusão.",
    }
    gravar_csv(SAIDA / "f1_por_classe.csv", linhas_csv, ["eixo", "classe", "f1", "suporte", "conclusao"])
    write_json(SAIDA / "resultado.json", payload)
    log_experiment("poc_tetrade_erros", {"gerou": True})
    print("matrizes gravadas para os quatro eixos")


def _png(eixo: str, grade: list[list[int]]) -> None:
    import matplotlib.pyplot as plt
    from _lib.plots import GREEN, PURPLE, apply_theme, save

    apply_theme()
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.imshow(grade, cmap="Purples")
    ax.set_xticks(range(len(CINCO_CLASSES)), list(CINCO_CLASSES), rotation=30, ha="right")
    ax.set_yticks(range(len(CINCO_CLASSES)), list(CINCO_CLASSES))
    ax.set_xlabel("Previsão")
    ax.set_ylabel("Rótulo humano")
    ax.set_title(eixo)
    for i, linha in enumerate(grade):
        for j, valor in enumerate(linha):
            ax.text(j, i, str(valor), ha="center", va="center", color=GREEN if valor else PURPLE)
    fig.tight_layout()
    save(fig, SAIDA / f"matriz_{eixo}.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
