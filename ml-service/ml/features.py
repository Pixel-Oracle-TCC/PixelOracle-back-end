"""Engenharia de features compartilhada entre treino (train.py) e API."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

from domain.risk import classify_period

LABEL_SOURCE_COL = "vendas_estimadas"

NUMERIC_FEATURES = [
    "platforms",
    "supported_languages",
    "dlc",
    "achievements",
    "metacritic",
    "price_brl",
    "release_year",
    "num_genres",
    "num_categories",
    "num_developers",
    "num_publishers",
    "required_age_num",
]

BOOLEAN_FEATURES = [
    "singleplayer",
    "multiplayer",
    "is_online",
    "indie",
    "early_access",
    "trading_cards",
    "workshop",
    "is_free",
    "coming_soon",
    "adult_content",
]

CATEGORICAL_FEATURES = [
    "controller_support",
    "type",
    "period_time",
    "main_genre",
]

REVIEW_FEATURES = [
    "total_positive",
    "total_reviews",
    "user_score",
    "multiplicador_boxleiter",
]


def include_review_features_from_env() -> bool:
    return os.getenv("INCLUDE_REVIEW_FEATURES", "true").lower() in ("1", "true", "yes")


def active_numeric_features(include_review_features: bool) -> List[str]:
    cols = list(NUMERIC_FEATURES)
    if include_review_features:
        cols.extend(REVIEW_FEATURES)
    return cols


def parse_price_brl(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return None
    cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_release_year(date_str: Any) -> Optional[int]:
    if not date_str:
        return None
    match = re.search(r"\d{4}", str(date_str))
    return int(match.group()) if match else None


def as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def parse_required_age(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def record_to_row(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai colunas utilizáveis de um documento Steam (JSON ou API)."""
    year = doc.get("release_year")
    if year is None:
        year = extract_release_year(doc.get("release_date") or doc.get("date"))

    genres = as_list(doc.get("genres"))
    categories = as_list(doc.get("categories"))
    period_time = doc.get("period_time") or classify_period(year)

    price = doc.get("price_brl")
    if price is None and "price_overview" in doc:
        price = parse_price_brl(doc.get("price_overview"))

    return {
        "app_id": doc.get("app_id"),
        "platforms": doc.get("platforms"),
        "supported_languages": doc.get("supported_languages"),
        "dlc": doc.get("dlc"),
        "achievements": doc.get("achievements"),
        "metacritic": doc.get("metacritic"),
        "price_brl": price,
        "release_year": year,
        "period_time": period_time,
        "num_genres": len(genres),
        "num_categories": len(categories),
        "num_developers": len(as_list(doc.get("developers"))),
        "num_publishers": len(as_list(doc.get("publishers"))),
        "required_age_num": parse_required_age(
            doc.get("required_age_num", doc.get("required_age"))
        ),
        "main_genre": genres[0] if genres else doc.get("main_genre"),
        "genres": genres,
        "categories": categories,
        "controller_support": doc.get("controller_support"),
        "type": doc.get("type"),
        "score_desc": doc.get("score_desc"),
        "singleplayer": bool(doc.get("singleplayer")),
        "multiplayer": bool(doc.get("multiplayer")),
        "is_online": bool(doc.get("is_online")),
        "indie": bool(doc.get("indie")),
        "early_access": bool(doc.get("early_access")),
        "trading_cards": bool(doc.get("trading_cards")),
        "workshop": bool(doc.get("workshop")),
        "is_free": bool(doc.get("is_free")),
        "coming_soon": bool(doc.get("coming_soon")),
        "adult_content": bool(doc.get("adult_content")),
        "total_positive": doc.get("total_positive", 0),
        "total_reviews": doc.get("total_reviews", 0),
        "user_score": doc.get("user_score", 0.0),
        "multiplicador_boxleiter": doc.get("multiplicador_boxleiter", 30),
        LABEL_SOURCE_COL: doc.get(LABEL_SOURCE_COL),
    }


def compute_score_desc_rare_labels(df: pd.DataFrame, min_count: int = 3) -> List[str]:
    if "score_desc" not in df.columns:
        return []
    counts = df["score_desc"].fillna("Desconhecido").value_counts()
    return [str(v) for v in counts[counts < min_count].index]


def sanitize_score_desc(
    df: pd.DataFrame,
    rare_labels: Optional[List[str]] = None,
) -> pd.DataFrame:
    if "score_desc" not in df.columns:
        return df
    df = df.copy()
    df["score_desc"] = df["score_desc"].fillna("Desconhecido")
    if rare_labels:
        rare_set = set(rare_labels)
        df["score_desc"] = df["score_desc"].replace({v: "Outros" for v in rare_set})
    return df


def build_feature_matrix(
    df: pd.DataFrame,
    genre_mlb: Optional[MultiLabelBinarizer] = None,
    category_mlb: Optional[MultiLabelBinarizer] = None,
    fit_encoders: bool = True,
    include_review_features: Optional[bool] = None,
) -> Tuple[pd.DataFrame, MultiLabelBinarizer, MultiLabelBinarizer]:
    if include_review_features is None:
        include_review_features = include_review_features_from_env()

    genre_mlb = genre_mlb or MultiLabelBinarizer()
    category_mlb = category_mlb or MultiLabelBinarizer()

    genre_lists = df["genres"].apply(as_list).tolist()
    category_lists = df["categories"].apply(as_list).tolist()

    if fit_encoders:
        genre_mat = genre_mlb.fit_transform(genre_lists)
        category_mat = category_mlb.fit_transform(category_lists)
    else:
        genre_mat = genre_mlb.transform(genre_lists)
        category_mat = category_mlb.transform(category_lists)

    genre_cols = [f"genre__{g}" for g in genre_mlb.classes_]
    category_cols = [f"category__{c}" for c in category_mlb.classes_]

    numeric_cols = active_numeric_features(include_review_features)
    parts = [
        df[numeric_cols].astype(float),
        df[BOOLEAN_FEATURES].astype(int),
    ]

    df_cat = df[CATEGORICAL_FEATURES].fillna("Desconhecido").astype(str)
    if include_review_features and "score_desc" in df.columns:
        df_cat = pd.concat(
            [df_cat, df[["score_desc"]].fillna("Desconhecido").astype(str)],
            axis=1,
        )

    parts.append(pd.get_dummies(df_cat, prefix=df_cat.columns, dtype=int))
    parts.append(pd.DataFrame(genre_mat, columns=genre_cols, index=df.index))
    parts.append(pd.DataFrame(category_mat, columns=category_cols, index=df.index))

    return pd.concat(parts, axis=1), genre_mlb, category_mlb


def prepare_inference_matrix(
    df: pd.DataFrame,
    genre_mlb: MultiLabelBinarizer,
    category_mlb: MultiLabelBinarizer,
    feature_columns: List[str],
    feature_config: Dict[str, Any],
) -> pd.DataFrame:
    """Pipeline idêntico ao treino para uma ou mais linhas de jogos."""
    rare_labels = feature_config.get("score_desc_rare", [])
    include_review = feature_config.get("include_review_features", True)

    df = sanitize_score_desc(df, rare_labels=rare_labels)
    df["price_brl"] = df["price_brl"].fillna(0.0)

    if df["genres"].apply(lambda g: len(as_list(g)) == 0).any():
        raise ValueError("Informe ao menos um gênero em 'genres'.")

    X, _, _ = build_feature_matrix(
        df,
        genre_mlb=genre_mlb,
        category_mlb=category_mlb,
        fit_encoders=False,
        include_review_features=include_review,
    )
    return X.reindex(columns=feature_columns, fill_value=0)
