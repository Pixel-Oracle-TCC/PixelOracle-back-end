"""Classificação de reviews pelos quatro eixos da Tétrade Elemental.

Pasta isolada. Não altera o restante do ml-service e não chama modelo nenhum.
"""

from tetrade.rotulo import para_binario, para_cinco, rotulo_eixo

__all__ = ["para_binario", "para_cinco", "rotulo_eixo"]
