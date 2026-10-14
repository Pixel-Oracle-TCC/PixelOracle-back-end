"""Regras de domínio: classificação de período e risco comercial."""

from typing import Dict, Optional

PRE_PANDEMIC_LABEL = "Pré-pandêmico"
POST_PANDEMIC_LABEL = "Pandêmico/Pós"
PANDEMIC_YEAR_THRESHOLD = 2020

RISK_LOW = "Baixo Risco (Sucesso)"
RISK_MEDIUM = "Risco Médio"
RISK_HIGH = "Alto Risco"

SALES_LOW_RISK = 50_000
SALES_MEDIUM_RISK = 10_000


def classify_period(year: Optional[int]) -> Optional[str]:
    if year is None:
        return None
    if year < PANDEMIC_YEAR_THRESHOLD:
        return PRE_PANDEMIC_LABEL
    return POST_PANDEMIC_LABEL


def create_risk_label(vendas: float) -> str:
    if vendas >= SALES_LOW_RISK:
        return RISK_LOW
    if vendas >= SALES_MEDIUM_RISK:
        return RISK_MEDIUM
    return RISK_HIGH


def success_chance_percent(
    probabilities: Optional[Dict[str, float]], predicted_class: str
) -> Optional[float]:
    """Probabilidade (0–100) da classe prevista = chance de sucesso estimada pelo modelo."""
    if not probabilities or predicted_class not in probabilities:
        return None
    return round(float(probabilities[predicted_class]) * 100, 1)
