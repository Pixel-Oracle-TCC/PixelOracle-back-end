"""Script offline: aplica schema SQL no Postgres."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from db.connection import get_engine, init_engine  # noqa: E402

SCHEMA_PATH = ML_ROOT / "db" / "migrations" / "001_schema.sql"


def main() -> None:
    engine = init_engine()
    if engine is None:
        raise SystemExit("DATABASE_URL não configurada.")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    # Remove bloco de comentários finais sobre índice; executa statements
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"✅ Schema aplicado: {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
