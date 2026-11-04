"""Caminhos, sessão do Postgres e gravação de saída. Não abre a Gemini."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = API_ROOT / "ml-service"
POC_ROOT = API_ROOT / "poc"

sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")


def open_session():
    from db.connection import init_engine, session_scope

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada em ml-service/.env.")
    return session_scope()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
