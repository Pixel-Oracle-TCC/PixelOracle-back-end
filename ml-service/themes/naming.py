"""Nomeação dos temas: a Gemini só dá nome ao cluster a partir de resumos reais.

Sem Gemini (ou se ela falhar), o rótulo é o resumo mais próximo do centróide —
sempre um texto que realmente saiu das reviews.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from absa.gemini_client import GeminiJsonClient, GeminiQuotaExceeded

logger = logging.getLogger(__name__)

PROMPT = """Abaixo há grupos de resumos de opiniões de jogadores, já agrupados por similaridade.
Para cada grupo, escreva um rótulo curto em português (3 a 7 palavras) que descreva o tema
comum, mantendo a polaridade (elogio ou crítica). Use só o que está nos resumos.

{groups}

Responda APENAS JSON: [{{"grupo": "<id>", "rotulo": "..."}}, ...]
"""


def name_clusters(
    clusters: Dict[str, dict],
    client: Optional[GeminiJsonClient] = None,
    chunk_size: int = 25,
) -> Dict[str, tuple[str, str]]:
    """
    clusters: {grupo_id: {"categoria", "polaridade", "amostras": [resumos]}}
    Retorna {grupo_id: (rotulo, fonte)} com fonte 'gemini' ou 'representante'.
    """
    labels: Dict[str, tuple[str, str]] = {
        gid: ((data["amostras"] or ["tema sem rótulo"])[0], "representante")
        for gid, data in clusters.items()
    }
    client = client or GeminiJsonClient()
    if not client.available:
        return labels

    ids = list(clusters.keys())
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]
        blocks: List[str] = []
        for gid in chunk:
            data = clusters[gid]
            polaridade = "elogio" if data["polaridade"] == "positivo" else "crítica"
            samples = "; ".join(data["amostras"][:8])
            blocks.append(f"Grupo {gid} ({data['categoria']}, {polaridade}): {samples}")
        try:
            parsed = client.generate_json(PROMPT.format(groups="\n".join(blocks)))
        except GeminiQuotaExceeded as exc:
            logger.warning("%s Restante dos temas fica com o representante.", exc)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nomeação via Gemini falhou; usando representantes. %s", exc)
            continue
        for item in parsed if isinstance(parsed, list) else []:
            gid = str(item.get("grupo"))
            rotulo = str(item.get("rotulo") or "").strip()
            if gid in labels and rotulo:
                labels[gid] = (rotulo[:80], "gemini")
    return labels
