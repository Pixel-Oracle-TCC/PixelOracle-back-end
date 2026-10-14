"""Registro do modelo carregado (estado da aplicação)."""

from typing import Optional

from infrastructure.artifacts import JoblibArtifactStore, LoadedModelBundle


class ModelRegistry:
    def __init__(self) -> None:
        self._bundle: Optional[LoadedModelBundle] = None
        self.error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self._bundle is not None

    def load(self, store: JoblibArtifactStore) -> None:
        self._bundle = store.load()
        self.error = None

    def set_error(self, message: str) -> None:
        self._bundle = None
        self.error = message

    def get_bundle(self) -> LoadedModelBundle:
        if not self._bundle:
            detail = self.error or "Modelo não carregado. Execute o treino antes de subir a API."
            raise ModelNotLoadedError(detail)
        return self._bundle


class ModelNotLoadedError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)
