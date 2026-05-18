"""Rotas HTTP — delegam aos casos de uso."""

from fastapi import APIRouter, HTTPException

from application.predict_risk import PredictCommercialRiskUseCase
from application.registry import ModelNotLoadedError, ModelRegistry
from presentation.schemas import GamePitchInput


def create_router(registry: ModelRegistry) -> APIRouter:
    router = APIRouter()
    predict_use_case = PredictCommercialRiskUseCase(registry)

    @router.get("/")
    def health():
        try:
            return predict_use_case.health_status()
        except ModelNotLoadedError as exc:
            raise HTTPException(status_code=503, detail=exc.detail) from exc

    @router.post("/predict")
    def predict_success(game: GamePitchInput):
        try:
            return predict_use_case.execute(game.model_dump())
        except ModelNotLoadedError as exc:
            raise HTTPException(status_code=503, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Erro ao processar predição: {exc}"
            ) from exc

    return router
