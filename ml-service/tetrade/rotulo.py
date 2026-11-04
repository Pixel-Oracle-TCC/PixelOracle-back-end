"""Do aspecto ao rótulo do eixo, como no manual de anotação (seção 7).

O rótulo não sai de uma impressão geral. Sai da contagem de aspectos distintos:
elogio (+), crítica (-) e neutro (0). Neutro não entra na conta de quem pesa mais.
"""

from __future__ import annotations

from typing import Iterable, Sequence

EIXOS = ("mecanica", "narrativa", "estetica", "tecnologia")

EIXO_NOME = {
    "mecanica": "Mecânica",
    "narrativa": "Narrativa",
    "estetica": "Estética",
    "tecnologia": "Tecnologia",
}

POSITIVO = "Positivo"
NEGATIVO = "Negativo"
NEUTRO = "Neutro"
MISTO_MAIS = "Misto (+)"
MISTO_IGUAL = "Misto (=)"
MISTO_MENOS = "Misto (−)"
NAO_MENCIONADO = "Não mencionado"
MISTO = "Misto"

SETE_CLASSES = (
    POSITIVO,
    NEGATIVO,
    NEUTRO,
    MISTO_MAIS,
    MISTO_IGUAL,
    MISTO_MENOS,
    NAO_MENCIONADO,
)
CINCO_CLASSES = (POSITIVO, NEGATIVO, NEUTRO, MISTO, NAO_MENCIONADO)

_MISTOS = {MISTO_MAIS, MISTO_IGUAL, MISTO_MENOS, MISTO, "Misto (-)"}


def rotulo_eixo(aspectos: Sequence[str]) -> str:
    """aspectos é uma lista de '+', '-' ou '0'. Lista vazia = Não mencionado."""
    sinais = [_normalizar_sinal(item) for item in aspectos]
    if not sinais:
        return NAO_MENCIONADO
    elogios = sinais.count("+")
    criticas = sinais.count("-")
    if elogios == 0 and criticas == 0:
        return NEUTRO
    if criticas == 0:
        return POSITIVO
    if elogios == 0:
        return NEGATIVO
    if elogios == criticas:
        return MISTO_IGUAL
    if elogios > criticas:
        return MISTO_MAIS
    return MISTO_MENOS


def para_cinco(rotulo: str) -> str:
    """Funde Misto (+), Misto (=) e Misto (−) em Misto, sem reanotar."""
    texto = (rotulo or "").strip()
    if texto in _MISTOS or texto.startswith("Misto"):
        return MISTO
    if texto not in CINCO_CLASSES and texto not in SETE_CLASSES:
        raise ValueError(f"Rótulo desconhecido: {rotulo}")
    return texto


def para_binario(rotulo: str) -> str:
    """Com juízo (elogio, crítica ou misto) contra o resto (neutro ou ausente)."""
    cinco = para_cinco(rotulo)
    if cinco in (POSITIVO, NEGATIVO, MISTO):
        return "com juízo"
    return "sem juízo"


def sinais_de_celula(texto: str) -> list[str]:
    """Lê 'combate+, dificuldade−' e devolve ['+', '-']. Vazio se a célula está em branco."""
    if texto is None or not str(texto).strip():
        return []
    sinais: list[str] = []
    for parte in str(texto).replace(";", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        sinais.append(_sinal_no_fim(parte))
    return sinais


def rotulo_bate_com_aspectos(rotulo_anotado: str, celula_aspectos: str) -> bool:
    """A planilha está consistente se o rótulo escrito é o que a contagem produz."""
    esperado = rotulo_eixo(sinais_de_celula(celula_aspectos))
    return _canon(rotulo_anotado) == _canon(esperado)


def _normalizar_sinal(item: str) -> str:
    texto = str(item).strip()
    if texto in {"+", "-", "0"}:
        return texto
    if texto in {"−"}:
        return "-"
    raise ValueError(f"Sinal de aspecto inválido: {item!r}. Use +, - ou 0.")


def _sinal_no_fim(parte: str) -> str:
    baixo = parte.casefold()
    if baixo.endswith("(+)") or parte.endswith("+"):
        return "+"
    if baixo.endswith("(-)") or baixo.endswith("(−)") or parte.endswith("-") or parte.endswith("−"):
        return "-"
    if baixo.endswith("(0)") or baixo.endswith("neutro") or parte.endswith("0"):
        return "0"
    raise ValueError(
        f"Aspecto sem sinal no fim: {parte!r}. O formato é combate+, dificuldade− ou trilha 0."
    )


def _canon(rotulo: str) -> str:
    texto = (rotulo or "").strip()
    if texto in {"Misto (-)", "Misto(-)"}:
        return MISTO_MENOS
    return texto


def conferir_exemplos(exemplos: Iterable[dict]) -> list[dict]:
    """Compara cada eixo de cada exemplo do manual com rotulo_eixo."""
    falhas: list[dict] = []
    for exemplo in exemplos:
        for eixo in EIXOS:
            bloco = exemplo["eixos"][eixo]
            obtido = rotulo_eixo(bloco["aspectos"])
            if _canon(obtido) != _canon(bloco["rotulo"]):
                falhas.append(
                    {
                        "id": exemplo["id"],
                        "eixo": eixo,
                        "esperado": bloco["rotulo"],
                        "obtido": obtido,
                    }
                )
    return falhas
