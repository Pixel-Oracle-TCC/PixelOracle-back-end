"""Ponto de entrada FastAPI — composição das camadas.

Lifespan: se DATABASE_URL existir, inicializa SQLAlchemy/pgvector. Não há mais modelo
para carregar no boot — o RF de drivers roda offline (ml/train_drivers.py) e grava os
resultados no banco.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

ML_SERVICE_DIR = Path(__file__).resolve().parent

if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from db.connection import get_database_url, init_engine  # noqa: E402
from presentation.routes import create_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_database_url():
        try:
            init_engine()
            print("✅ Conexão PostgreSQL inicializada.")
        except Exception as exc:
            print(f"⚠️  Postgres configurado mas falhou ao conectar: {exc}")
    else:
        print("ℹ️  DATABASE_URL ausente — /analyze e /retrieve-similar ficam indisponíveis.")
    yield


app = FastAPI(
    title="Pixel Oracle - ML API",
    description=(
        "Dashboard de evidências a partir de reviews reais da Steam: jogos similares "
        "(pgvector), temas recorrentes (ABSA + cluster), recorrência estatística e "
        "drivers de recomendação (Random Forest)."
    ),
    lifespan=lifespan,
)

app.include_router(create_router())
