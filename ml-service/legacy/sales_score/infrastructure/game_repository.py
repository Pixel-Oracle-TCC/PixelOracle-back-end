"""Adapters para leitura de jogos (JSON local ou MongoDB)."""

import json
import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ml.features import record_to_row


class JsonGameRepository:
    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def load_dataframe(self) -> pd.DataFrame:
        if not self._json_path.is_file():
            raise FileNotFoundError(f"Arquivo de dados não encontrado: {self._json_path}")

        print(f"📂 Carregando dados de {self._json_path}...")
        with open(self._json_path, encoding="utf-8") as handle:
            records = json.load(handle)

        df = pd.DataFrame(record_to_row(doc) for doc in records)
        print(f"📦 Foram carregados {len(df)} jogos do JSON!")
        return df


class MongoGameRepository:
    def __init__(self, uri: str, database: str, collection: str) -> None:
        self._uri = uri
        self._database = database
        self._collection = collection

    def load_dataframe(self) -> pd.DataFrame:
        from pymongo import MongoClient

        print("🔌 Conectando ao MongoDB...")
        client = MongoClient(self._uri)
        try:
            docs = list(
                client[self._database][self._collection].find({}, {"_id": 0})
            )
        finally:
            client.close()

        df = pd.DataFrame(record_to_row(doc) for doc in docs)
        print(f"📦 Foram extraídos {len(df)} jogos do MongoDB!")
        return df


def create_game_repository(
    ml_service_dir: Path,
    json_path: Optional[Path] = None,
) -> Union[JsonGameRepository, MongoGameRepository]:
    source = os.getenv("DATA_SOURCE", "json").lower()
    if source == "mongo":
        mongo_uri = os.getenv("MONGO_URI")
        mongo_db = os.getenv("MONGO_DB")
        mongo_collection = os.getenv("MONGO_COLLECTION")
        missing = [
            name
            for name, value in [
                ("MONGO_URI", mongo_uri),
                ("MONGO_DB", mongo_db),
                ("MONGO_COLLECTION", mongo_collection),
            ]
            if not value
        ]
        if missing:
            raise ValueError(f"Variáveis ausentes: {', '.join(missing)}")
        return MongoGameRepository(mongo_uri, mongo_db, mongo_collection)

    default_json = ml_service_dir / "data" / "database_steam_br.json"
    path = Path(json_path or os.getenv("DATA_JSON_PATH", default_json))
    return JsonGameRepository(path)
