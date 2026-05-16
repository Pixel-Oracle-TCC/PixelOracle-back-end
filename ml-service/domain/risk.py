"""Regras de domínio: classificação de período e risco comercial."""

from typing import Optional

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
