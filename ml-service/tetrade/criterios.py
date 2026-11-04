"""Limites de go/no-go fixados antes de ver qualquer resultado de modelo.

Nenhuma prova desta rodada preenche esses limites. Eles existem para não serem
escolhidos depois de olhar o número.
"""

from __future__ import annotations

CRITERIOS = {
    "kappa_medio_entre_anotadores_minimo": 0.6,
    "macro_f1_medio_minimo": 0.60,
    "eixos_que_precisam_passar_do_piso": ["mecanica", "estetica"],
    "transformer_precisa_superar": "tfidf_regressao_logistica",
    "minimo_de_exemplos_para_concluir_sobre_uma_classe": 30,
    "teste_humano_reviews": [100, 150],
    "declaracao": (
        "Estes limites são a proposta do documento da Tétrade. "
        "Esta rodada não declara go, go com ajustes nem no-go de modelo, "
        "porque não há dois anotadores nem treino de transformer."
    ),
}
