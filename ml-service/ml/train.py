"""Pipeline de treinamento e persistência de artefatos."""

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
    compute_score_desc_rare_labels,
    include_review_features_from_env,
    sanitize_score_desc,
)

ARTIFACTS_DIR = ML_SERVICE_DIR / "artifacts"

load_dotenv(ML_SERVICE_DIR / ".env")


def prepare_training_data(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, MultiLabelBinarizer, MultiLabelBinarizer, list]:
    score_desc_rare = compute_score_desc_rare_labels(df)
    df = sanitize_score_desc(df, rare_labels=score_desc_rare)

    required = [LABEL_SOURCE_COL, "period_time", "main_genre"]
    df = df.dropna(subset=required).copy()
    df = df[df[LABEL_SOURCE_COL] > 0].copy()
    df["price_brl"] = df["price_brl"].fillna(0.0)
    df = df[df["genres"].apply(lambda g: len(as_list(g)) > 0)].copy()

    y = df[LABEL_SOURCE_COL].apply(create_risk_label)
    include_review = include_review_features_from_env()
    X, genre_mlb, category_mlb = build_feature_matrix(
        df, fit_encoders=True, include_review_features=include_review
    )
    return X, y, genre_mlb, category_mlb, score_desc_rare


def build_classifier() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def train_and_save(df: pd.DataFrame) -> None:
    print("🧹 Preparando features (todas as colunas do JSON)...")
    X, y, genre_mlb, category_mlb, score_desc_rare = prepare_training_data(df)
    include_review = include_review_features_from_env()

    print(f"   → Amostras: {len(X)} | Features: {X.shape[1]}")
    print(f"   → Gêneros (multi-hot): {len(genre_mlb.classes_)}")
    print(f"   → Categorias Steam (multi-hot): {len(category_mlb.classes_)}")

    if include_review:
        warnings.warn(
            "INCLUDE_REVIEW_FEATURES=true: total_reviews e correlatos vazam informação "
            "do alvo (vendas_estimadas = reviews × multiplicador). "
            "Use INCLUDE_REVIEW_FEATURES=false para simular predição pré-lançamento.",
            UserWarning,
            stacklevel=2,
        )

    clf = build_classifier()

    print("\n🔁 Validação cruzada (5-fold, amostra pequena)...")
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
    for name, score in top.items():
        print(f"   {score:.4f}  {name}")

    print(f"\n💾 Salvando artefatos em {ARTIFACTS_DIR}...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, ARTIFACTS_DIR / "modelo_rf.pkl")
    joblib.dump(genre_mlb, ARTIFACTS_DIR / "mlb_genres.pkl")
    joblib.dump(category_mlb, ARTIFACTS_DIR / "mlb_categories.pkl")
    joblib.dump(list(X.columns), ARTIFACTS_DIR / "feature_columns.pkl")
    joblib.dump(
        {
            "numeric": active_numeric_features(include_review),
            "boolean": BOOLEAN_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "include_review_features": include_review,
            "include_score_desc": include_review,
            "score_desc_rare": score_desc_rare,
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
