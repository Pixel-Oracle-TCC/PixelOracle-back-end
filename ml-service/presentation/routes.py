"""Rotas HTTP — health, retrieve-similar, analyze.

Camada fina: valida input (Pydantic), chama caso de uso, traduz exceções em HTTP.
Regra de negócio NÃO fica aqui — ver application/*.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from application.analyze import AnalyzePitchUseCase, RetrieveSimilarUseCase
from db.connection import get_database_url, session_scope
from presentation.schemas import GamePitchInput, RetrieveSimilarInput

ENDPOINTS = ["/", "/health", "/retrieve-similar", "/analyze"]
COUNTED_TABLES = ("games", "reviews", "review_aspects", "themes", "theme_stats", "genre_drivers")


def _require_db() -> None:
    if not get_database_url():
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL não configurada — o dashboard depende do Postgres.",
        )


def create_router() -> APIRouter:
    router = APIRouter()
    retrieve_use_case = RetrieveSimilarUseCase()
    analyze_use_case = AnalyzePitchUseCase()

    def _health_payload() -> Dict[str, Any]:
        # Sempre 200: o healthcheck do Docker não pode derrubar o serviço por banco vazio
        payload: Dict[str, Any] = {
            "status": "online",
            "modo": "pre-lancamento",
            "database_configured": bool(get_database_url()),
            "endpoints": ENDPOINTS,
        }
        if not get_database_url():
            return payload
        try:
            session = session_scope()
            try:
                payload["contagens"] = {
                    table: session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                    for table in COUNTED_TABLES
                }
            finally:
                session.close()
            payload["database_ok"] = True
        except Exception as exc:  # noqa: BLE001
            payload["database_ok"] = False
            payload["database_error"] = str(exc)[:200]
        return payload

    @router.get("/")
    def root_health():
        return _health_payload()

    @router.get("/health")
    def health():
        return _health_payload()

    @router.post("/retrieve-similar")
    def retrieve_similar(body: RetrieveSimilarInput):
        """RAG isolado. Exige DATABASE_URL (embeddings no Postgres)."""
        _require_db()
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

    @router.post("/analyze")
    def analyze(game: GamePitchInput):
        """Endpoint principal consumido por /api/report: dashboard de evidências de reviews."""
        _require_db()
        try:
            session = session_scope()
            try:
                return analyze_use_case.execute(session, game.model_dump())
            finally:
                session.close()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Erro ao montar o dashboard: {exc}"
            ) from exc

    return router
