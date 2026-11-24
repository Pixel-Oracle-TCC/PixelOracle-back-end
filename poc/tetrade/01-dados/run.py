"""Prova 1. A amostra em português entra sem autor e sem texto repetido."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import AMOSTRA_IDS, DADOS, gravar_csv, open_session, write_json
from ml.experiments import log_experiment
from models.orm import Game, Review
from sqlalchemy import text
from tetrade.amostra import colunas_de_autor, preparar

SAIDA = Path(__file__).resolve().parent / "output"


def main() -> None:
    session = open_session()
    try:
        colunas = [
            row[0]
            for row in session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'reviews' "
                    "ORDER BY ordinal_position"
                )
            )
        ]
        vazadas = colunas_de_autor(colunas)
        registros = [
            {
                "review_id": row.id,
                "game_id": row.game_id,
                "titulo": row.titulo,
                "texto": row.texto or "",
            }
            for row in session.query(Review.id, Review.game_id, Review.texto, Game.titulo)
            .join(Game, Game.id == Review.game_id)
            .filter(Review.language == "brazilian")
        ]
    finally:
        session.close()

    resumo = preparar(registros)
    amostra = resumo.pop("amostra")
    por_jogo = resumo.pop("por_jogo")
    gravar_csv(
        AMOSTRA_IDS,
        amostra,
        ["review_id", "game_id", "titulo", "n_palavras"],
    )
    gravar_csv(DADOS / "por_jogo.csv", por_jogo, ["game_id", "titulo", "reviews"])
    payload = {
        "hipotese": "A amostra em português não tem coluna de autor e não repete o mesmo texto no mesmo jogo.",
        "o_que_isto_nao_e": "Não é uma coleta nova na Steam e não é um modelo.",
        "idioma": "brazilian",
        "colunas_de_reviews": colunas,
        "colunas_de_autor": vazadas,
        "passou_sem_autor": not vazadas,
        **resumo,
        "reviews_na_amostra": len(amostra),
        "arquivo_de_ids": str(AMOSTRA_IDS),
    }
    write_json(SAIDA / "resultado.json", payload)
    _grafico(payload)
    log_experiment("poc_tetrade_dados", {"passou_sem_autor": payload["passou_sem_autor"], "reviews_na_amostra": len(amostra)})
    print(f"amostra: {len(amostra)} reviews em {payload['jogos_na_amostra']} jogos | autor: {vazadas or 'nenhuma coluna'}")
    if vazadas:
        raise SystemExit(1)


def _grafico(payload: dict) -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import matplotlib.pyplot as plt
    from _lib.plots import GREEN, GREEN_SOFT, PURPLE, apply_theme, save

    rotulos = ["Na amostra", "Curtas demais", "Longas demais", "Texto repetido", "Quase sem letra"]
    valores = [
        payload["reviews_na_amostra"],
        payload["curtos_menos_de_20"],
        payload["longos_mais_de_200"],
        payload["duplicatas_no_mesmo_jogo"] + payload["extras_removidos_entre_jogos"],
        payload["ilegivel_ou_sem_letra"],
    ]
    cores = [GREEN, PURPLE, "#9D4EDD", GREEN_SOFT, "#5A189A"]
    apply_theme()
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh(rotulos[::-1], valores[::-1], color=cores[::-1])
    ax.set_xlabel("Reviews em português")
    ax.set_title("O que ficou na amostra da Tétrade")
    save(fig, SAIDA / "amostra.png")


if __name__ == "__main__":
    main()
