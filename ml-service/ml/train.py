"""Treinamento do modelo em modo pré-lançamento (sem reviews na matriz de features).

Por quê strip de reviews no X: incluir score/reviews pós-lançamento inflava a
acurácia (~95%) com leakage. Modo honesto (~55% CV) usa só metadados planejáveis.
Hiperparâmetros em build_classifier(); mudanças → /experiments/random_forest.md.
Ver vault: [[Por que Random Forest]].
"""

import os
import sys
import warnings
from pathlib import Path
from typing import Tuple

ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import MultiLabelBinarizer

from domain.risk import create_risk_label
from infrastructure.game_repository import create_game_repository
from ml.features import (
    BOOLEAN_FEATURES,
    CATEGORICAL_FEATURES,
    LABEL_SOURCE_COL,
    active_numeric_features,
    as_list,
    build_feature_matrix,
    strip_for_prelaunch_training,
)

ARTIFACTS_DIR = ML_SERVICE_DIR / "artifacts"

load_dotenv(ML_SERVICE_DIR / ".env")


def prepare_training_data(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, MultiLabelBinarizer, MultiLabelBinarizer]:
    """
    Treina como se o dev informasse apenas o planejamento (preço, gêneros, categorias…).
    O rótulo (vendas_estimadas) vem do histórico Steam, mas reviews NÃO entram no X.
    """
    if LABEL_SOURCE_COL not in df.columns:
        raise ValueError(f"Dataset precisa da coluna {LABEL_SOURCE_COL} para treino.")

    required = [LABEL_SOURCE_COL, "period_time", "main_genre"]
    df = df.dropna(subset=required).copy()
    df = df[df[LABEL_SOURCE_COL] > 0].copy()
    df["price_brl"] = df["price_brl"].fillna(0.0)
    df = df[df["genres"].apply(lambda g: len(as_list(g)) > 0)].copy()

    # y vem do histórico (vendas_estimadas); X NÃO pode ver reviews do mesmo jogo
    y = df[LABEL_SOURCE_COL].apply(create_risk_label)

    # Apenas metadados planejáveis antes do lançamento (preço, gêneros, flags…)
    df_features = strip_for_prelaunch_training(df)
    X, genre_mlb, category_mlb = build_feature_matrix(
        df_features, fit_encoders=True, include_review_features=False
    )
    return X, y, genre_mlb, category_mlb


def build_classifier() -> RandomForestClassifier:
    # class_weight=balanced: classes de risco costumam ser desbalanceadas na base BR
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def train_and_save(df: pd.DataFrame) -> None:
    print("🧹 Treinamento modo PRÉ-LANÇAMENTO (sem reviews / score_desc nas features)...")
    X, y, genre_mlb, category_mlb = prepare_training_data(df)

    print(f"   → Amostras: {len(X)} | Features: {X.shape[1]}")
    print(f"   → Gêneros (multi-hot): {len(genre_mlb.classes_)}")
    print(f"   → Categorias Steam (multi-hot): {len(category_mlb.classes_)}")
    print("   → titulo/descricao: usados na API e no Gemini; não entram no ML")

    clf = build_classifier()

    print("\n🔁 Validação cruzada (5-fold)...")
    cv_scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    print(f"   → Acurácia CV: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

    print("\n🧠 Treinamento final (hold-out 20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    clf.fit(X_train, y_train)

    print("\n📊 Classification Report (teste):")
    previsoes = clf.predict(X_test)
    print(classification_report(y_test, previsoes, zero_division=0))

    importances = pd.Series(clf.feature_importances_, index=X.columns)
    top = importances.sort_values(ascending=False).head(15)
    print("\n🔝 Top 15 features por importância:")
    for feat, score in top.items():
        print(f"   {score:.4f}  {feat}")

    print(f"\n💾 Salvando artefatos em {ARTIFACTS_DIR}...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, ARTIFACTS_DIR / "modelo_rf.pkl")
    joblib.dump(genre_mlb, ARTIFACTS_DIR / "mlb_genres.pkl")
    joblib.dump(category_mlb, ARTIFACTS_DIR / "mlb_categories.pkl")
    joblib.dump(list(X.columns), ARTIFACTS_DIR / "feature_columns.pkl")
    joblib.dump(
        {
            "modo": "pre-lancamento",
            "numeric": active_numeric_features(False),
            "boolean": BOOLEAN_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "include_review_features": False,
            "include_score_desc": False,
            "score_desc_rare": [],
        },
        ARTIFACTS_DIR / "feature_config.pkl",
    )

    print("✅ Pipeline concluído com sucesso!")


if __name__ == "__main__":
    try:
        repository = create_game_repository(ML_SERVICE_DIR)
        df = repository.load_dataframe()
        train_and_save(df)
    except Exception as exc:
        print(f"❌ Erro no pipeline de treino: {exc}")
        raise SystemExit(1) from exc
