"""Mapeamento do pitch do desenvolvedor → payload só com features do ML."""

from typing import Any, Dict

# Narrativa do dev (não entra no modelo)
PITCH_ONLY_FIELDS = frozenset({
    "titulo",
    "descricao",
    "ideia",
    "name",
    "description",
    "game_name",
    "idea_description",
})

# Indisponíveis antes do lançamento na Steam
POST_LAUNCH_FIELDS = frozenset({
    "total_positive",
    "total_reviews",
    "user_score",
    "multiplicador_boxleiter",
    "score_desc",
    "vendas_estimadas",
})


def normalize_pitch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Unifica aliases (name → titulo, ideia → descricao)."""
    data = dict(payload)
    if not data.get("titulo"):
        data["titulo"] = data.get("name") or data.get("game_name")
    if not data.get("descricao"):
        data["descricao"] = (
            data.get("ideia") or data.get("description") or data.get("idea_description")
        )
    return data


def to_ml_payload(pitch: Dict[str, Any]) -> Dict[str, Any]:
    """Remove título, descrição e KPIs pós-lançamento antes da inferência."""
    normalized = normalize_pitch(pitch)
    return {
        k: v
        for k, v in normalized.items()
        if k not in PITCH_ONLY_FIELDS and k not in POST_LAUNCH_FIELDS
    }
