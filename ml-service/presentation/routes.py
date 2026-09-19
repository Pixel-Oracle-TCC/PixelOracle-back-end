"""Rotas HTTP — predict, retrieve-similar, triangulate, health.

Camada fina: valida input (Pydantic), chama caso de uso, traduz exceções em HTTP.
Regra de negócio NÃO fica aqui — ver application/*.
"""

from fastapi import APIRouter, HTTPException

from application.predict_risk import PredictCommercialRiskUseCase
from application.registry import ModelNotLoadedError, ModelRegistry
from application.triangulate import RetrieveSimilarUseCase, TriangulateUseCase
from db.connection import get_database_url, session_scope
from presentation.schemas import GamePitchInput, RetrieveSimilarInput


def create_router(registry: ModelRegistry) -> APIRouter:
    router = APIRouter()
    predict_use_case = PredictCommercialRiskUseCase(registry)
    retrieve_use_case = RetrieveSimilarUseCase()
    triangulate_use_case = TriangulateUseCase(registry)

    def _health_payload():
        try:
            base = predict_use_case.health_status()
        except ModelNotLoadedError as exc:
            raise HTTPException(status_code=503, detail=exc.detail) from exc
        # Frontend/ops: saber se RAG está disponível sem olhar .env
        base["database_configured"] = bool(get_database_url())
        base["endpoints"] = ["/", "/health", "/predict", "/retrieve-similar", "/triangulate"]
        return base

    @router.get("/")
    def root_health():
        return _health_payload()

    @router.get("/health")
    def health():
        return _health_payload()

    @router.post("/predict")
    def predict_success(game: GamePitchInput):
        """Só Random Forest — compatível com telas que não precisam do dashboard."""
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

    @router.post("/retrieve-similar")
    def retrieve_similar(body: RetrieveSimilarInput):
        """RAG isolado. Exige DATABASE_URL (embeddings no Postgres)."""
        if not get_database_url():
            raise HTTPException(
                status_code=503,
                detail="DATABASE_URL não configurada — retrieval indisponível.",
            )
        try:
            session = session_scope()
            try:
                return retrieve_use_case.execute(
                    session,
                    titulo=body.titulo,
                    descricao=body.descricao,
                    genres=body.genres,
                    top_k=body.top_k,
                )
            finally:
                session.close()
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Erro na busca de similares: {exc}"
            ) from exc

    @router.post("/triangulate")
    def triangulate(game: GamePitchInput):
        """
        Endpoint principal consumido por /api/report.
        Sem DB: degrada para RF-only (aviso no JSON) em vez de 503 —
        o report do produto continua útil.
        """
        try:
            if not get_database_url():
                return triangulate_use_case.execute_without_db(game.model_dump())
            session = session_scope()
            try:
                return triangulate_use_case.execute(session, game.model_dump())
            finally:
                session.close()
        except ModelNotLoadedError as exc:
            raise HTTPException(status_code=503, detail=exc.detail) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Erro na triangulação: {exc}"
            ) from exc

    return router
