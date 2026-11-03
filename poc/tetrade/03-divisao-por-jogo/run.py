"""Prova 3. Treino, validação e teste não compartilham jogo nem texto."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import AMOSTRA_IDS, DIVISAO, gravar_csv, ler_csv, ler_json, open_session, write_json
from ml.experiments import log_experiment
from models.orm import Review
from tetrade.amostra import chave_texto
from tetrade.divisao import dividir_por_jogo, textos_vazam

SAIDA = Path(__file__).resolve().parent / "output"


def main() -> None:
    if not AMOSTRA_IDS.exists():
        raise SystemExit("Rode a prova 1 antes. Falta poc/tetrade/dados/amostra_ids.csv.")
    ids = ler_csv(AMOSTRA_IDS)
    registros = [
        {
            "review_id": int(row["review_id"]),
            "game_id": int(row["game_id"]),
            "titulo": row["titulo"],
        }
        for row in ids
    ]
    if DIVISAO.exists():
        divisao = ler_json(DIVISAO)
        origem = "arquivo salvo"
    else:
        divisao = dividir_por_jogo(registros)
        origem = "criada nesta execução"
        write_json(DIVISAO, divisao)

    textos = _textos([int(row["review_id"]) for row in ids])
    com_texto = []
    for row in registros:
        item = dict(row)
        item["texto"] = textos.get(item["review_id"], "")
        com_texto.append(item)
    vazamento = textos_vazam(com_texto, divisao, chave_texto)
    jogos = {nome: set(map(int, ids_jogo)) for nome, ids_jogo in divisao["conjuntos"].items()}
    intersecao = {
        "treino_validacao": sorted(jogos["treino"] & jogos["validacao"]),
        "treino_teste": sorted(jogos["treino"] & jogos["teste"]),
        "validacao_teste": sorted(jogos["validacao"] & jogos["teste"]),
    }
    conhecidos = jogos["treino"] | jogos["validacao"] | jogos["teste"]
    novos = sorted({row["game_id"] for row in registros} - conhecidos)
    payload = {
        "hipotese": "Treino, validação e teste não compartilham jogo nem o mesmo texto.",
        "o_que_isto_nao_e": "O teste ainda não foi anotado por duas pessoas. Ele fica reservado.",
        "origem_da_divisao": origem,
        "arquivo": str(DIVISAO),
        "reviews": divisao["reviews"],
        "jogos": divisao["jogos"],
        "teste_dentro_da_faixa_100_a_150": divisao["teste_dentro_da_faixa"],
        "intersecao_de_jogos": intersecao,
        "textos_em_mais_de_um_conjunto": len(vazamento),
        "jogos_da_amostra_fora_da_divisao_salva": novos,
        "passou": not any(intersecao.values()) and not vazamento and not novos,
    }
    write_json(SAIDA / "resultado.json", payload)
    gravar_csv(
        SAIDA / "conjuntos.csv",
        [
            {"conjunto": nome, "game_id": game_id}
            for nome, lista in divisao["conjuntos"].items()
            for game_id in lista
        ],
        ["conjunto", "game_id"],
    )
    _grafico(divisao["reviews"])
    log_experiment(
        "poc_tetrade_divisao",
        {"passou": payload["passou"], "reviews": divisao["reviews"], "origem": origem},
    )
    print(
        f"origem: {origem} | teste: {divisao['reviews']['teste']} reviews | passou: {payload['passou']}"
    )
    if not payload["passou"]:
        raise SystemExit(1)


def _textos(ids: list[int]) -> dict[int, str]:
    session = open_session()
    try:
        saida = {}
        for inicio in range(0, len(ids), 1000):
            bloco = ids[inicio : inicio + 1000]
            for row in session.query(Review.id, Review.texto).filter(Review.id.in_(bloco)):
                saida[int(row.id)] = row.texto or ""
        return saida
    finally:
        session.close()


def _grafico(reviews: dict) -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import matplotlib.pyplot as plt
    from _lib.plots import GREEN, GREEN_SOFT, PURPLE, apply_theme, save

    nomes = ["Treino", "Validação", "Teste"]
    chaves = ["treino", "validacao", "teste"]
    apply_theme()
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.bar(nomes, [reviews[chave] for chave in chaves], color=[GREEN, GREEN_SOFT, PURPLE])
    ax.set_ylabel("Reviews")
    ax.set_title("Divisão por jogo. O teste não entra no treino.")
    save(fig, SAIDA / "divisao.png")


if __name__ == "__main__":
    main()
