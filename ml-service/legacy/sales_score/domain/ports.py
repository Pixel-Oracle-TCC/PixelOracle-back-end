"""Ports (interfaces) para adapters de infraestrutura."""

from typing import Any, Dict, List, Protocol

import pandas as pd


class GameDataSource(Protocol):
    def load_dataframe(self) -> pd.DataFrame: ...


class ModelBundle(Protocol):
    model: Any
    genre_mlb: Any
    category_mlb: Any
    feature_columns: List[str]
    feature_config: Dict[str, Any]
