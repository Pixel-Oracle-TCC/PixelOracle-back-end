"""Script offline: aplica todas as migrations SQL em ordem (001, 002, ...).

As migrations são idempotentes (IF NOT EXISTS), então rodar de novo é seguro.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from db.connection import init_engine  # noqa: E402

MIGRATIONS_DIR = ML_ROOT / "db" / "migrations"


def main() -> None:
    engine = init_engine()
    if engine is None:
        raise SystemExit("DATABASE_URL não configurada.")
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        # exec_driver_sql: o SQL tem blocos DO $$ e ':' em comentários, que text() trataria como bind
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
        print(f"✅ Migration aplicada: {path.name}")


if __name__ == "__main__":
    main()
