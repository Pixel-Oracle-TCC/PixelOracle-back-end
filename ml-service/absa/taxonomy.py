"""Categorias fixas de aspecto (camada estável do modelo híbrido de temas).

Os subtemas finos ("crashes no lançamento", "história emocionante") são descobertos por
cluster dentro de cada categoria — ver scripts/cluster_themes.py.
"""

from __future__ import annotations

CATEGORIES = {
    "gameplay": "mecânicas, combate, loop principal, diversão",
    "controles": "resposta dos comandos, input, suporte a controle",
    "dificuldade": "desafio, curva de aprendizado, balanceamento",
    "historia": "enredo, narrativa, roteiro, final",
    "personagens": "carisma, desenvolvimento e escrita dos personagens",
    "graficos": "arte, visual, direção de arte, animações",
    "audio": "trilha sonora, efeitos, dublagem",
    "performance": "FPS, otimização, travamentos, requisitos",
    "bugs": "erros, glitches, saves corrompidos",
    "conteudo": "duração, quantidade de conteúdo, rejogabilidade",
    "progressao": "ritmo, grind, sistema de evolução, recompensas",
    "preco": "custo-benefício, preço, microtransações",
    "multiplayer": "online, servidores, matchmaking, coop",
    "suporte_dev": "atualizações, comunicação e postura do estúdio",
    "outros": "qualquer outro aspecto relevante",
}

SENTIMENTS = ("positivo", "negativo", "neutro")
POLARITIES = ("positivo", "negativo")


def normalize_category(value: str) -> str:
    key = (value or "").strip().lower().replace("ó", "o").replace("á", "a").replace("ç", "c")
    key = key.replace("ã", "a").replace("é", "e").replace("ú", "u").replace(" ", "_")
    return key if key in CATEGORIES else "outros"


def normalize_sentiment(value: str) -> str:
    key = (value or "").strip().lower()
    return key if key in SENTIMENTS else "neutro"
