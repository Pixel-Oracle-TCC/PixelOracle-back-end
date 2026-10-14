"""Carregamento de artefatos treinados (joblib)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import joblib

REQUIRED_ARTIFACT_FILES = (
    "modelo_rf.pkl",
    "mlb_genres.pkl",
    "mlb_categories.pkl",
    "feature_columns.pkl",
    "feature_config.pkl",
)


@dataclass
class LoadedModelBundle:
    model: Any
    genre_mlb: Any
    category_mlb: Any
    feature_columns: List[str]
    feature_config: Dict[str, Any]


class JoblibArtifactStore:
    def __init__(self, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir

    def missing_files(self) -> List[str]:
        return [
            name
            for name in REQUIRED_ARTIFACT_FILES
            if not (self._artifacts_dir / name).is_file()
        ]

    def load(self) -> LoadedModelBundle:
        missing = self.missing_files()
        if missing:
            raise FileNotFoundError(
                f"Artefatos ausentes em {self._artifacts_dir}: {', '.join(missing)}. "
                "Execute: python ml/train.py"
            )

        return LoadedModelBundle(
            model=joblib.load(self._artifacts_dir / "modelo_rf.pkl"),
            genre_mlb=joblib.load(self._artifacts_dir / "mlb_genres.pkl"),
            category_mlb=joblib.load(self._artifacts_dir / "mlb_categories.pkl"),
            feature_columns=joblib.load(self._artifacts_dir / "feature_columns.pkl"),
            feature_config=joblib.load(self._artifacts_dir / "feature_config.pkl"),
        )
