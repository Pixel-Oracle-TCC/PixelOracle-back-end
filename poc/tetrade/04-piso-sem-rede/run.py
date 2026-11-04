"""Prova 4. O piso sem rede neural, só se existir planilha humana."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import DIVISAO, PREDICOES, ROTULOS, gravar_csv, ler_csv, ler_json, write_json
from ml.experiments import log_experiment
from tetrade.baselines import escolher_c, prever_majoritaria, treinar
from tetrade.criterios import CRITERIOS
from tetrade.metricas import agrupar_por_jogo, bootstrap_por_jogo, f1_por_classe, macro_f1
from tetrade.rotulo import CINCO_CLASSES, EIXOS, MISTO_IGUAL, MISTO_MAIS, MISTO_MENOS, para_binario, para_cinco, rotulo_bate_com_aspectos

SAIDA = Path(__file__).resolve().parent / "output"
ASPECTOS = {
    "mecanica": "aspectos_mecanica",
    "narrativa": "aspectos_narrativa",
    "estetica": "aspectos_estetica",
    "tecnologia": "aspectos_tecnologia",
}


def main() -> None:
    if not ROTULOS.exists():
        payload = _sem_planilha()
        write_json(SAIDA / "resultado.json", payload)
        log_experiment("poc_tetrade_piso", {"treinou": False, "motivo": payload["motivo"]})
        print(payload["motivo"])
        return
    if not DIVISAO.exists():
        raise SystemExit("Rode a prova 3 antes. Falta a divisão por jogo.")

    divisao = ler_json(DIVISAO)
    conjunto_de = {}
    for nome, ids in divisao["conjuntos"].items():
        for game_id in ids:
            conjunto_de[int(game_id)] = nome
    linhas = []
    inconsistencias = 0
    for row in ler_csv(ROTULOS):
        game_id = int(row["game_id"]) if row.get("game_id") else _game_id(row, conjunto_de)
        if game_id is None:
            continue
        conjunto = conjunto_de.get(game_id)
        if conjunto is None:
            continue
        item = {
            "review_id": int(row["review_id"]),
            "game_id": game_id,
            "texto": row.get("texto") or "",
            "conjunto": conjunto,
            "anotador": row.get("anotador") or "",
        }
        for eixo in EIXOS:
            item[eixo] = para_cinco(row[eixo])
            item[eixo + "_7"] = row[eixo].strip()
            celula = row.get(ASPECTOS[eixo], "")
            if celula and not rotulo_bate_com_aspectos(row[eixo], celula):
                inconsistencias += 1
        linhas.append(item)

    treino = [row for row in linhas if row["conjunto"] == "treino"]
    val = [row for row in linhas if row["conjunto"] == "validacao"]
    teste = [row for row in linhas if row["conjunto"] == "teste"]
    if len(treino) < 20 or not val:
        payload = {
            "treinou": False,
            "motivo": "A planilha não tem rótulos suficientes no treino e na validação. O teste não foi usado para compensar.",
            "rotulos_treino": len(treino),
            "rotulos_validacao": len(val),
            "rotulos_teste_nao_usados": len(teste),
            "inconsistencias_aspecto_rotulo": inconsistencias,
            "criterios_fixados_antes": CRITERIOS,
            "decisao": "sem go",
        }
        write_json(SAIDA / "resultado.json", payload)
        log_experiment("poc_tetrade_piso", {"treinou": False, "motivo": payload["motivo"]})
        print(payload["motivo"])
        return

    eixos = {}
    predicoes = []
    grupos_boot: dict = {}
    for eixo in EIXOS:
        y_treino = [row[eixo] for row in treino]
        y_val = [row[eixo] for row in val]
        textos_treino = [row["texto"] for row in treino]
        textos_val = [row["texto"] for row in val]
        grupos = [row["game_id"] for row in treino]
        c = escolher_c(textos_treino, y_treino, grupos)
        modelo = treinar(textos_treino, y_treino, c)
        major = prever_majoritaria(y_treino, len(val))
        if modelo is None:
            tfidf = major
            c = None
        else:
            tfidf = [str(item) for item in modelo.predict(textos_val)]
        eixos[eixo] = {
            "c": c,
            "classe_majoritaria": major[0],
            "macro_f1_majoritaria": macro_f1(y_val, major, CINCO_CLASSES),
            "macro_f1_tfidf": macro_f1(y_val, tfidf, CINCO_CLASSES),
            "f1_por_classe_tfidf": f1_por_classe(y_val, tfidf, CINCO_CLASSES),
            "binario_macro_f1_tfidf": _binario(treino, val, eixo),
        }
        agrupar_por_jogo([row["game_id"] for row in val], eixo, y_val, tfidf, grupos_boot)
        for row, chute in zip(val, tfidf):
            predicoes.append(
                {
                    "review_id": row["review_id"],
                    "game_id": row["game_id"],
                    "eixo": eixo,
                    "verdade": row[eixo],
                    "previsto_tfidf": chute,
                }
            )

    medias_maj = [bloco["macro_f1_majoritaria"] for bloco in eixos.values()]
    medias_tf = [bloco["macro_f1_tfidf"] for bloco in eixos.values()]
    payload = {
        "treinou": True,
        "esquema": "5 classes",
        "conjunto_avaliado": "validacao",
        "teste_nao_foi_usado": True,
        "rotulos_teste_nao_usados": len(teste),
        "inconsistencias_aspecto_rotulo": inconsistencias,
        "macro_f1_medio_majoritaria": round(sum(medias_maj) / len(medias_maj), 4),
        "macro_f1_medio_tfidf": round(sum(medias_tf) / len(medias_tf), 4),
        "bootstrap_tfidf": bootstrap_por_jogo(grupos_boot, CINCO_CLASSES),
        "eixos": eixos,
        "sete_classes": _sete(treino),
        "criterios_fixados_antes": CRITERIOS,
        "decisao": "sem go",
        "o_que_isto_nao_e": "Não é o resultado do BERTimbau e não é o teste humano final.",
    }
    gravar_csv(PREDICOES, predicoes, ["review_id", "game_id", "eixo", "verdade", "previsto_tfidf"])
    write_json(SAIDA / "resultado.json", payload)
    log_experiment("poc_tetrade_piso", {"treinou": True, "macro_f1_medio_tfidf": payload["macro_f1_medio_tfidf"]})
    print(f"tfidf macro-F1 médio na validação: {payload['macro_f1_medio_tfidf']}")


def _sem_planilha() -> dict:
    return {
        "treinou": False,
        "motivo": (
            "Não há poc/tetrade/dados/rotulos.csv. Sem rótulo humano não existe F1. "
            "O arquivo de exemplo está em rotulos.csv.exemplo."
        ),
        "criterios_fixados_antes": CRITERIOS,
        "decisao": "sem go",
        "o_que_isto_nao_e": "A ausência de número não é um F1 zero.",
    }


def _game_id(row: dict, conjunto_de: dict[int, str]) -> int | None:
    if row.get("game_id"):
        return int(row["game_id"])
    return None


def _binario(treino: list[dict], val: list[dict], eixo: str) -> float | None:
    y_treino = [para_binario(row[eixo]) for row in treino]
    y_val = [para_binario(row[eixo]) for row in val]
    modelo = treinar([row["texto"] for row in treino], y_treino, 1.0)
    if modelo is None:
        return None
    previsto = [str(item) for item in modelo.predict([row["texto"] for row in val])]
    return macro_f1(y_val, previsto, ["com juízo", "sem juízo"])


def _sete(treino: list[dict]) -> dict:
    contagem = {MISTO_MAIS: 0, MISTO_IGUAL: 0, MISTO_MENOS: 0}
    for row in treino:
        for eixo in EIXOS:
            rotulo = row[eixo + "_7"]
            if rotulo in contagem:
                contagem[rotulo] += 1
    suficiente = all(valor >= 30 for valor in contagem.values())
    return {
        "contagem_no_treino": contagem,
        "treinou_7_classes": False,
        "motivo": (
            "As três classes mistas têm pelo menos 30 exemplos no treino, mas o esquema principal desta POC é o de 5 classes."
            if suficiente
            else "Alguma classe mista tem menos de 30 exemplos no treino. O esquema de 7 classes não foi treinado."
        ),
    }


if __name__ == "__main__":
    main()
