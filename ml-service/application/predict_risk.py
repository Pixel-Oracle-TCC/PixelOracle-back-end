"""Caso de uso: prever risco comercial de um jogo."""

from typing import Any, Dict

import pandas as pd

from application.registry import ModelRegistry
from domain.risk import classify_period
from ml.features import prepare_inference_matrix, record_to_row


class PredictCommercialRiskUseCase:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def health_status(self) -> Dict[str, Any]:
        bundle = self._registry.get_bundle()
        return {
            "status": "online",
            "model_loaded": self._registry.loaded,
            "features": len(bundle.feature_columns),
            "include_review_features": bundle.feature_config.get("include_review_features"),
        }

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        bundle = self._registry.get_bundle()

        if not payload.get("period_time"):
            payload = {**payload, "period_time": classify_period(payload["release_year"])}

        row = record_to_row(payload)
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

        return {
            "status": "sucesso",
            "kpis_analisados": len(bundle.feature_columns),
            "previsao_pixel_oracle": {
                "risco_comercial": str(prediction),
                "probabilidades": probabilities,
            },
        }
