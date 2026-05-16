"""Camada HTTP (FastAPI)."""

from presentation.routes import create_router
from presentation.schemas import GameDataInput

__all__ = ["GameDataInput", "create_router"]
