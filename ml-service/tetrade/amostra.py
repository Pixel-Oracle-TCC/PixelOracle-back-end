"""Filtros do manual antes da anotação: tamanho, duplicata e texto sem letras."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Iterable, Mapping, Sequence

MIN_PALAVRAS = 20
MAX_PALAVRAS = 200
_ESPACOS = re.compile(r"\s+")


def n_palavras(texto: str) -> int:
    return len(_ESPACOS.sub(" ", (texto or "").strip()).split()) if (texto or "").strip() else 0


def chave_texto(texto: str) -> str:
    """Mesmo texto com espaços e maiúsculas diferentes conta como duplicata."""
    dobrado = unicodedata.normalize("NFKC", texto or "").casefold()
    return _ESPACOS.sub(" ", dobrado).strip()


def parece_ilegivel(texto: str) -> bool:
    """ASCII art e sequência quase sem letra. Não tenta entender ironia."""
    bruto = texto or ""
    if not bruto.strip():
        return True
    letras = sum(1 for char in bruto if char.isalpha())
    return letras / len(bruto) < 0.4


def preparar(registros: Sequence[Mapping]) -> dict:
    """registros: review_id, game_id, titulo, texto.

    Mantém um único exemplar de cada texto igual. O primeiro id, o menor, fica.
    Textos fora de 20–200 palavras e textos ilegíveis saem da amostra e entram na contagem.
    """
    por_jogo_antes: dict[int, int] = defaultdict(int)
    grupos: dict[tuple, list] = defaultdict(list)
    ilegivel = 0
    for row in registros:
        por_jogo_antes[int(row["game_id"])] += 1
        if parece_ilegivel(row.get("texto") or ""):
            ilegivel += 1
            continue
        grupos[(int(row["game_id"]), chave_texto(row.get("texto") or ""))].append(row)

    duplicatas_no_jogo = 0
    unicos = []
    for rows in grupos.values():
        ordenados = sorted(rows, key=lambda item: int(item["review_id"]))
        unicos.append(ordenados[0])
        duplicatas_no_jogo += len(ordenados) - 1

    por_texto: dict[str, set[int]] = defaultdict(set)
    for row in unicos:
        por_texto[chave_texto(row.get("texto") or "")].add(int(row["game_id"]))
    repetidos_entre_jogos = 0
    mantidos = []
    ja_visto: set[str] = set()
    for row in sorted(unicos, key=lambda item: int(item["review_id"])):
        chave = chave_texto(row.get("texto") or "")
        if chave in ja_visto:
            repetidos_entre_jogos += 1
            continue
        ja_visto.add(chave)
        mantidos.append(row)
    textos_em_mais_de_um_jogo = sum(1 for jogos in por_texto.values() if len(jogos) > 1)

    fora_do_tamanho = 0
    curtos = 0
    longos = 0
    amostra = []
    for row in mantidos:
        palavras = n_palavras(row.get("texto") or "")
        if palavras < MIN_PALAVRAS:
            fora_do_tamanho += 1
            curtos += 1
            continue
        if palavras > MAX_PALAVRAS:
            fora_do_tamanho += 1
            longos += 1
            continue
        amostra.append({**dict(row), "n_palavras": palavras})

    por_jogo: dict[int, dict] = {}
    for row in amostra:
        jogo = por_jogo.setdefault(
            int(row["game_id"]),
            {"game_id": int(row["game_id"]), "titulo": row.get("titulo") or "", "reviews": 0},
        )
        jogo["reviews"] += 1

    return {
        "lidas": len(registros),
        "ilegivel_ou_sem_letra": ilegivel,
        "duplicatas_no_mesmo_jogo": duplicatas_no_jogo,
        "textos_iguais_em_jogos_diferentes": textos_em_mais_de_um_jogo,
        "extras_removidos_entre_jogos": repetidos_entre_jogos,
        "fora_de_20_a_200_palavras": fora_do_tamanho,
        "curtos_menos_de_20": curtos,
        "longos_mais_de_200": longos,
        "amostra": amostra,
        "por_jogo": sorted(por_jogo.values(), key=lambda item: (-item["reviews"], item["game_id"])),
        "jogos_antes": len(por_jogo_antes),
        "jogos_na_amostra": len(por_jogo),
    }


def colunas_de_autor(nomes: Iterable[str]) -> list[str]:
    proibidos = ("steamid", "author", "persona", "profileurl", "realname")
    achados = []
    for nome in nomes:
        baixo = nome.casefold()
        if any(token in baixo for token in proibidos):
            achados.append(nome)
    return achados
