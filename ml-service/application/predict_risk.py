"""Caso de uso: prever risco e chances de sucesso (pré-lançamento)."""

from typing import Any, Dict

import pandas as pd

from application.payload import normalize_pitch, to_ml_payload
from application.registry import ModelRegistry
from domain.risk import classify_period, success_chance_percent
from ml.features import prepare_inference_matrix, record_to_row


class PredictCommercialRiskUseCase:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def health_status(self) -> Dict[str, Any]:
        bundle = self._registry.get_bundle()
        return {
            "status": "online",
            "model_loaded": self._registry.loaded,
            "modo": "pre-lancamento",
            "features": len(bundle.feature_columns),
            "include_review_features": bundle.feature_config.get(
                "include_review_features", False
            ),
            "mensagem": (
                "Informe titulo, descricao da ideia e metadados planejados. "
                "Reviews não são necessárias — o jogo ainda não foi lançado."
            ),
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        bundle = self._registry.get_bundle()
        pitch = normalize_pitch(payload)
        ml_payload = to_ml_payload(pitch)

        if not pitch.get("titulo") or not pitch.get("descricao"):
            raise ValueError("Campos obrigatórios: titulo e descricao (ideia do jogo).")

        if not ml_payload.get("period_time"):
            ml_payload = {
                **ml_payload,
                "period_time": classify_period(ml_payload["release_year"]),
            }

        row = record_to_row(ml_payload)
        df = pd.DataFrame([row])

        features = prepare_inference_matrix(
            df,
            genre_mlb=bundle.genre_mlb,
            category_mlb=bundle.category_mlb,
            feature_columns=bundle.feature_columns,
            feature_config=bundle.feature_config,
        )

        prediction = bundle.model.predict(features)[0]
        probabilities = None
        if hasattr(bundle.model, "predict_proba"):
            classes = list(bundle.model.classes_)
            proba = bundle.model.predict_proba(features)[0]
            probabilities = {
                cls: round(float(probability), 4)
                for cls, probability in zip(classes, proba)
            }

        chance = success_chance_percent(probabilities, str(prediction))

        return {
            "status": "sucesso",
            "modo": "pre-lancamento",
            "jogo": {
                "titulo": pitch["titulo"],
                "descricao": pitch["descricao"],
            },
            "kpis_analisados": len(bundle.feature_columns),
            "previsao_pixel_oracle": {
                "risco_comercial": str(prediction),
                "chance_sucesso_estimada_pct": chance,
                "probabilidades": probabilities,
            },
        }
