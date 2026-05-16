"""Ponto de entrada FastAPI — composição das camadas."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

ML_SERVICE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_SERVICE_DIR / "artifacts"

if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from application.registry import ModelRegistry  # noqa: E402
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
        registry.set_error(str(exc))
        print(f"❌ Falha ao carregar artefatos: {exc}")
    yield


app = FastAPI(
    title="Pixel Oracle - ML API",
    description="Predição de risco comercial para jogos Steam BR (pipeline alinhado ao treino).",
    lifespan=lifespan,
)

app.include_router(create_router(registry))
