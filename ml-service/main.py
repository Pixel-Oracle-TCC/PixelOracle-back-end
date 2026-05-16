import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ML_SERVICE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_SERVICE_DIR / "artifacts"

if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from model.features import (  # noqa: E402
    classify_period,
    prepare_inference_matrix,
    record_to_row,
)


class ModelState:
    def __init__(self) -> None:
        self.model = None
        self.genre_mlb = None
        self.category_mlb = None
        self.feature_columns: List[str] = []
        self.feature_config: Dict[str, Any] = {}
        self.loaded = False
        self.error: Optional[str] = None


state = ModelState()


def load_artifacts() -> None:
    required_files = [
        "modelo_rf.pkl",
        "mlb_genres.pkl",
        "mlb_categories.pkl",
        "feature_columns.pkl",
        "feature_config.pkl",
    ]
    missing = [f for f in required_files if not (ARTIFACTS_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Artefatos ausentes em {ARTIFACTS_DIR}: {', '.join(missing)}. "
            "Execute: python model/train.py"
        )

    state.model = joblib.load(ARTIFACTS_DIR / "modelo_rf.pkl")
    state.genre_mlb = joblib.load(ARTIFACTS_DIR / "mlb_genres.pkl")
    state.category_mlb = joblib.load(ARTIFACTS_DIR / "mlb_categories.pkl")
    state.feature_columns = joblib.load(ARTIFACTS_DIR / "feature_columns.pkl")
    state.feature_config = joblib.load(ARTIFACTS_DIR / "feature_config.pkl")
    state.loaded = True
    state.error = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🧠 Carregando modelo e encoders...")
    try:
        load_artifacts()
        print(f"✅ Modelo pronto ({len(state.feature_columns)} features).")
    except Exception as exc:
        state.loaded = False
        state.error = str(exc)
        print(f"❌ Falha ao carregar artefatos: {exc}")
    yield


app = FastAPI(
    title="Pixel Oracle - ML API",
    description="Predição de risco comercial para jogos Steam BR (pipeline alinhado ao treino).",
    lifespan=lifespan,
)


class GameDataInput(BaseModel):
    """Payload alinhado ao schema de database_steam_br.json / train.py."""

    price_brl: float = Field(..., ge=0, description="Preço em reais (ex: 11.39)")
    genres: List[str] = Field(..., min_length=1, description='Ex: ["Ação", "Indie"]')
    categories: List[str] = Field(
        ..., min_length=1, description='Ex: ["Um jogador", "Proezas Steam"]'
    )

    release_year: int = Field(..., ge=1990, le=2035)
    period_time: Optional[str] = Field(
        None, description='Opcional. Ex: "Pandêmico/Pós" ou "Pré-pandêmico"'
    )

    platforms: int = Field(1, ge=0)
    supported_languages: int = Field(1, ge=0)
    dlc: int = Field(0, ge=0)
    achievements: int = Field(0, ge=0)
    metacritic: int = Field(0, ge=0)
    required_age_num: float = Field(0, ge=0)

    singleplayer: bool = True
    multiplayer: bool = False
    is_online: bool = False
    indie: bool = True
    early_access: bool = False
    trading_cards: bool = False
    workshop: bool = False
    is_free: bool = False
    coming_soon: bool = False
    adult_content: bool = False

    controller_support: str = "none"
    type: str = "game"
    score_desc: str = "Mixed"

    total_positive: int = Field(0, ge=0)
    total_reviews: int = Field(0, ge=0)
    user_score: float = Field(0.0, ge=0, le=100)
    multiplicador_boxleiter: int = Field(30, ge=1)


def _ensure_model_ready() -> None:
    if not state.loaded:
        detail = state.error or "Modelo não carregado. Execute o treino antes de subir a API."
        raise HTTPException(status_code=503, detail=detail)


@app.get("/")
def health():
    _ensure_model_ready()
    return {
        "status": "online",
        "model_loaded": state.loaded,
        "features": len(state.feature_columns),
        "include_review_features": state.feature_config.get("include_review_features"),
    }


@app.post("/predict")
def predict_success(game: GameDataInput):
    _ensure_model_ready()

    try:
        payload = game.model_dump()
        if not payload.get("period_time"):
            payload["period_time"] = classify_period(payload["release_year"])

        row = record_to_row(payload)
        df = pd.DataFrame([row])

        X = prepare_inference_matrix(
            df,
            genre_mlb=state.genre_mlb,
            category_mlb=state.category_mlb,
            feature_columns=state.feature_columns,
            feature_config=state.feature_config,
        )

        prediction = state.model.predict(X)[0]
        probabilities = None
        if hasattr(state.model, "predict_proba"):
            classes = list(state.model.classes_)
            proba = state.model.predict_proba(X)[0]
            probabilities = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}

        return {
            "status": "sucesso",
            "kpis_analisados": len(state.feature_columns),
            "previsao_pixel_oracle": {
                "risco_comercial": str(prediction),
                "probabilidades": probabilities,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar predição: {exc}"
        ) from exc
