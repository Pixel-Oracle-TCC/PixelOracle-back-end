"""Adapters: persistência, artefatos ML e fontes de dados."""

from infrastructure.artifacts import JoblibArtifactStore, LoadedModelBundle
from infrastructure.game_repository import create_game_repository

__all__ = [
    "JoblibArtifactStore",
    "LoadedModelBundle",
    "create_game_repository",
]
