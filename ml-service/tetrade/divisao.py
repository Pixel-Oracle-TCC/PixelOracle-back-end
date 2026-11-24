"""Divide reviews por jogo. O mesmo jogo não aparece em dois conjuntos."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Mapping, Sequence

SEMENTE = 42
TESTE_MIN = 100
TESTE_MAX = 150


def dividir_por_jogo(
    registros: Sequence[Mapping],
    *,
    semente: int = SEMENTE,
    teste_min: int = TESTE_MIN,
    teste_max: int = TESTE_MAX,
) -> dict:
    """Reserva um teste de 100 a 150 reviews em jogos que não vão para o treino.

    Jogo com mais reviews do que o teto do teste não entra no teste: um jogo só
    estouraria a faixa. O resto dos jogos vai 80% para treino e 20% para validação.
    """
    por_jogo: dict[int, list[int]] = defaultdict(list)
    titulos: dict[int, str] = {}
    for row in registros:
        game_id = int(row["game_id"])
        por_jogo[game_id].append(int(row["review_id"]))
        titulos[game_id] = row.get("titulo") or titulos.get(game_id) or ""
    for ids in por_jogo.values():
        ids.sort()

    pequenos = [game_id for game_id, ids in por_jogo.items() if len(ids) <= teste_max]
    grandes = [game_id for game_id, ids in por_jogo.items() if len(ids) > teste_max]
    rng = random.Random(semente)
    rng.shuffle(pequenos)

    teste: list[int] = []
    resto: list[int] = []
    n_teste = 0
    for game_id in pequenos:
        tamanho = len(por_jogo[game_id])
        if n_teste >= teste_min:
            resto.append(game_id)
            continue
        if n_teste + tamanho > teste_max:
            resto.append(game_id)
            continue
        teste.append(game_id)
        n_teste += tamanho

    pool = resto + grandes
    rng_pool = random.Random(semente + 1)
    rng_pool.shuffle(pool)
    if len(pool) <= 1:
        validacao: list[int] = []
        treino = list(pool)
    else:
        n_val = max(1, round(0.2 * len(pool)))
        validacao = pool[:n_val]
        treino = pool[n_val:]

    conjuntos = {"treino": treino, "validacao": validacao, "teste": teste}
    _sem_intersecao(conjuntos)
    return {
        "semente": semente,
        "teste_min": teste_min,
        "teste_max": teste_max,
        "conjuntos": {nome: sorted(ids) for nome, ids in conjuntos.items()},
        "reviews": {nome: _contar(ids, por_jogo) for nome, ids in conjuntos.items()},
        "jogos": {nome: len(ids) for nome, ids in conjuntos.items()},
        "teste_dentro_da_faixa": teste_min <= n_teste <= teste_max,
        "jogos_grandes_fora_do_teste": sorted(grandes),
        "titulos": {str(game_id): titulos[game_id] for game_id in sorted(por_jogo)},
    }


def textos_vazam(registros: Sequence[Mapping], divisao: Mapping, chave) -> list[str]:
    """Devolve textos cuja chave aparece em mais de um conjunto."""
    jogo_de = {}
    for nome, ids in divisao["conjuntos"].items():
        for game_id in ids:
            jogo_de[int(game_id)] = nome
    onde: dict[str, set[str]] = defaultdict(set)
    for row in registros:
        conjunto = jogo_de.get(int(row["game_id"]))
        if conjunto is None:
            continue
        onde[chave(row.get("texto") or "")].add(conjunto)
    return [texto for texto, conjuntos in onde.items() if len(conjuntos) > 1]


def _contar(game_ids: Sequence[int], por_jogo: Mapping[int, Sequence[int]]) -> int:
    return sum(len(por_jogo[game_id]) for game_id in game_ids)


def _sem_intersecao(conjuntos: Mapping[str, Sequence[int]]) -> None:
    nomes = list(conjuntos)
    for i, esquerda in enumerate(nomes):
        for direita in nomes[i + 1 :]:
            comum = set(conjuntos[esquerda]) & set(conjuntos[direita])
            if comum:
                raise RuntimeError(f"Jogo nos dois conjuntos {esquerda} e {direita}: {sorted(comum)[:5]}")
