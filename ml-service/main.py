"""Ponto de entrada FastAPI — composição das camadas.

Lifespan:
1) Carrega artefatos do Random Forest (obrigatório para /predict e /triangulate).
2) Se DATABASE_URL existir, inicializa SQLAlchemy/pgvector (RAG + insights).
Sem DB o serviço sobe mesmo assim — predict ok; retrieve/RAG degradam.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

ML_SERVICE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_SERVICE_DIR / "artifacts"

if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from application.registry import ModelRegistry  # noqa: E402
from db.connection import get_database_url, init_engine  # noqa: E402
from infrastructure.artifacts import JoblibArtifactStore  # noqa: E402
from presentation.routes import create_router  # noqa: E402

registry = ModelRegistry()
artifact_store = JoblibArtifactStore(ARTIFACTS_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🧠 Carregando modelo e encoders...")
    try:
        registry.load(artifact_store)
        bundle = registry.get_bundle()
        print(f"✅ Modelo pronto ({len(bundle.feature_columns)} features).")
    except Exception as exc:
        # Mantém o processo vivo com erro no registry → rotas devolvem 503
        registry.set_error(str(exc))
        print(f"❌ Falha ao carregar artefatos: {exc}")

    if get_database_url():
        try:
            init_engine()
            print("✅ Conexão PostgreSQL inicializada.")
        except Exception as exc:
            print(f"⚠️  Postgres configurado mas falhou ao conectar: {exc}")
    else:
        print("ℹ️  DATABASE_URL ausente — /predict ok; /retrieve-similar e RAG limitados.")

    yield


app = FastAPI(
    title="Pixel Oracle - ML API",
    description=(
        "Motor de triangulação: Random Forest + RAG (pgvector) + ABSA/genre_insights. "
        "Estima risco comercial pré-lançamento e gera dashboard estruturado."
    ),
    lifespan=lifespan,
)

app.include_router(create_router(registry))
