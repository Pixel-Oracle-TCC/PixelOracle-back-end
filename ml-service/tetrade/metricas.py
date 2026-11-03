"""Macro-F1, matriz de confusão e intervalo por reamostragem de jogos."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Mapping, Sequence

from sklearn.metrics import confusion_matrix, f1_score


def macro_f1(verdade: Sequence[str], previsto: Sequence[str], classes: Sequence[str]) -> float | None:
    if not verdade:
        return None
    return round(float(f1_score(verdade, previsto, labels=list(classes), average="macro", zero_division=0)), 4)


def f1_por_classe(verdade: Sequence[str], previsto: Sequence[str], classes: Sequence[str]) -> dict[str, dict]:
    pontuacoes = f1_score(verdade, previsto, labels=list(classes), average=None, zero_division=0)
    saida = {}
    for classe, valor in zip(classes, pontuacoes):
        suporte = sum(1 for item in verdade if item == classe)
        saida[classe] = {
            "f1": round(float(valor), 4),
            "suporte": suporte,
            "conclusao": suporte >= 30,
        }
    return saida


def matriz(verdade: Sequence[str], previsto: Sequence[str], classes: Sequence[str]) -> list[list[int]]:
    bruta = confusion_matrix(verdade, previsto, labels=list(classes))
    return [[int(valor) for valor in linha] for linha in bruta]


def bootstrap_por_jogo(
    por_jogo: Mapping[int, Mapping[str, tuple[Sequence[str], Sequence[str]]]],
    classes: Sequence[str],
    *,
    n: int = 400,
    semente: int = 42,
) -> dict:
    """Reamostra jogos inteiros. por_jogo[game][eixo] = (verdade, previsto)."""
    jogos = sorted(por_jogo)
    if len(jogos) < 2:
        return {"motivo": "Menos de dois jogos na validação. O intervalo não se calcula."}
    rng = random.Random(semente)
    medias = []
    for _ in range(n):
        amostra = [rng.choice(jogos) for _ in jogos]
        valores = []
        for eixo in _eixos(por_jogo):
            verdade: list[str] = []
            previsto: list[str] = []
            for game_id in amostra:
                par = por_jogo[game_id].get(eixo)
                if par is None:
                    continue
                verdade.extend(par[0])
                previsto.extend(par[1])
            valor = macro_f1(verdade, previsto, classes)
            if valor is not None:
                valores.append(valor)
        if valores:
            medias.append(round(sum(valores) / len(valores), 4))
    medias.sort()
    if not medias:
        return {"motivo": "Não houve métrica nas reamostras."}
    baixo = medias[int(0.025 * (len(medias) - 1))]
    alto = medias[int(0.975 * (len(medias) - 1))]
    return {
        "reamostras": n,
        "jogos": len(jogos),
        "macro_f1_medio": round(sum(medias) / len(medias), 4),
        "intervalo_95": [baixo, alto],
    }


def agrupar_por_jogo(
    game_ids: Sequence[int],
    eixo: str,
    verdade: Sequence[str],
    previsto: Sequence[str],
    destino: dict[int, dict[str, tuple[list[str], list[str]]]] | None = None,
) -> dict[int, dict[str, tuple[list[str], list[str]]]]:
    grupos: dict[int, dict[str, tuple[list[str], list[str]]]] = destino if destino is not None else defaultdict(dict)
    baldes: dict[int, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
    for game_id, certo, chute in zip(game_ids, verdade, previsto):
        baldes[int(game_id)][0].append(certo)
        baldes[int(game_id)][1].append(chute)
    for game_id, par in baldes.items():
        grupos[game_id][eixo] = par
    return grupos


def _eixos(por_jogo: Mapping[int, Mapping[str, tuple]]) -> list[str]:
    nomes: list[str] = []
    for bloco in por_jogo.values():
        for nome in bloco:
            if nome not in nomes:
                nomes.append(nome)
    return nomes
