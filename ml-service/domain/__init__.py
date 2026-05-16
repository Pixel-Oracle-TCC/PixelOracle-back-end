"""Regras de negócio e contratos (sem dependência de frameworks)."""

from domain.risk import classify_period, create_risk_label

__all__ = ["classify_period", "create_risk_label"]
