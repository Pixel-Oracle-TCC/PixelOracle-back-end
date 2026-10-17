"""Testes unitários sintéticos do pipeline de reviews (sem rede e sem banco).

Uso: python scripts/test_pipeline.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import requests

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))

from absa.extractor import AbsaExtractor, is_literal_excerpt  # noqa: E402
from absa.gemini_client import GeminiQuotaExceeded, _is_daily_quota  # noqa: E402
from absa.significance import (  # noqa: E402
    benjamini_hochberg,
    compute_theme_stats,
    quote_rank_key,
    wilson_interval,
)
from absa.validation import cohen_kappa, multilabel_f1, multilabel_kappa, parse_annotation  # noqa: E402
from collection.catalog import (  # noqa: E402
    genre_names,
    parse_release_date,
    parse_supported_languages,
    rank_top_sellers,
    rejection_reason,
)
from collection.reviews_client import (  # noqa: E402
    ReviewsClient,
    is_usable_review_text,
    normalize_review_text,
)
from ml.drivers import build_driver_matrix, train_drivers  # noqa: E402
from themes.clustering import NOISE, cluster_embeddings  # noqa: E402
from triangulation.engine import TriangulationEngine  # noqa: E402


def test_sanitize_review_drops_author_identity() -> None:
    raw = {
        "recommendationid": "123",
        "review": "Ótimo jogo",
        "voted_up": True,
        "votes_up": 10,
        "weighted_vote_score": "0.8",
        "developer_response": "Obrigado!",
        "received_for_free": False,
        "author": {"steamid": "7656119", "playtime_at_review": 300, "num_games_owned": 50},
    }
    clean = ReviewsClient.sanitize_review(raw, fatia="proporcional")
    assert clean is not None
    assert "author" not in clean and "steamid" not in str(clean)
    assert clean["playtime_at_review"] == 300
    assert clean["weighted_vote_score"] == 0.8
    assert clean["developer_response"] == "Obrigado!"
    assert clean["fatias"] == ["proporcional"]
    assert ReviewsClient.sanitize_review({"review": "sem id"}, fatia="proporcional") is None


def test_quality_filter_rejects_junk() -> None:
    assert is_usable_review_text("The combat feels amazing and the story is deep.")
    assert not is_usable_review_text("lol")
    assert not is_usable_review_text("!!!!!!!!!!??????????")
    assert normalize_review_text("  Hello   World  ") == "hello world"


def test_catalog_filters_software_and_canonicalizes_genres() -> None:
    jogo = {
        "type": "game",
        "genres": [
            {"id": "1", "description": "Ação"},
            {"id": "18", "description": "Esportes"},
            {"id": "73", "description": "Violento"},
        ],
    }
    assert rejection_reason(jogo) is None
    assert genre_names(jogo) == ["Ação", "Desporto"]
    wallpaper = {"type": "game", "genres": [{"id": "4"}, {"id": "57", "description": "Utilitários"}]}
    assert rejection_reason(wallpaper) == "software"
    assert rejection_reason({"type": "dlc", "genres": []}) == "tipo dlc"
    assert rejection_reason(None) == "sem página na Store BR"


def test_parse_release_date_and_languages() -> None:
    from datetime import date

    assert parse_release_date({"release_date": {"date": "24/fev./2022"}}) == date(2022, 2, 24)
    assert parse_release_date({"release_date": {"date": "Feb 24, 2022"}}) == date(2022, 2, 24)
    langs = parse_supported_languages(
        {"supported_languages": "Inglês<strong>*</strong>, Português (Brasil), Japonês"}
    )
    assert langs == ["Inglês", "Português (Brasil)", "Japonês"]


def test_top_sellers_rewards_consistency() -> None:
    def week(*appids):
        return [{"rank": i, "appid": a, "item": {"name": str(a), "type": 0}} for i, a in enumerate(appids, 1)]

    dlc = {"rank": 1, "appid": 99, "item": {"name": "DLC", "type": 4}}
    # 10 é 1º só numa semana (pico de lançamento); 20 fica em 2º nas três
    weeks = [week(10, 20), week(30, 20), [dlc] + week(40, 20)[1:]]
    ranking = rank_top_sellers(weeks)
    assert [s.appid for s in ranking][0] == 20
    assert ranking[0].semanas == 3 and ranking[0].pontos == 3 * 99
    assert 99 not in {s.appid for s in ranking}


def test_literal_excerpt_check() -> None:
    texto = "The combat feels   amazing, but the story is forgettable."
    assert is_literal_excerpt("combat feels amazing", texto)
    assert not is_literal_excerpt("best story ever", texto)


def test_extractor_cleans_and_validates() -> None:
    aspects = AbsaExtractor._clean_aspects(
        [
            {"categoria": "Gameplay", "sentimento": "positivo", "trecho": "combat feels amazing", "resumo": "combate bom"},
            {"categoria": "inexistente", "sentimento": "???", "trecho": "inventado", "resumo": "algo"},
            {"categoria": "gameplay", "sentimento": "positivo", "trecho": "x", "resumo": "combate bom"},
        ],
        "The combat feels amazing",
    )
    assert len(aspects) == 2
    assert aspects[0]["categoria"] == "gameplay" and aspects[0]["trecho_literal"] is True
    assert aspects[1]["categoria"] == "outros" and aspects[1]["sentimento"] == "neutro"
    assert aspects[1]["trecho_literal"] is False


def test_extractor_stops_on_daily_quota() -> None:
    class QuotaClient:
        model = "fake"
        calls = 0

        def generate_json(self, prompt: str) -> list:
            QuotaClient.calls += 1
            if QuotaClient.calls > 1:
                raise GeminiQuotaExceeded("cota")
            return [{"id": "1", "aspectos": []}]

    extractor = AbsaExtractor(client=QuotaClient(), sleep_seconds=0)
    reviews = [{"recommendationid": str(i), "texto": "texto qualquer"} for i in range(25)]
    results = extractor.extract_batch(reviews, batch_size=10)
    # 1º lote gravável; ao bater a cota, para sem tentar os lotes seguintes
    assert extractor.quota_exhausted and QuotaClient.calls == 2
    assert set(results) == {str(i) for i in range(10)}

    response = requests.Response()
    response.status_code = 429
    response._content = json.dumps(
        {"error": {"details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}
    ).encode()
    assert _is_daily_quota(response)
    response._content = b'{"error": {"details": []}}'
    assert not _is_daily_quota(response)


def test_wilson_and_bh() -> None:
    low, high = wilson_interval(20, 100)
    assert 0.13 < low < 0.2 < high < 0.29
    assert wilson_interval(0, 0) == (0.0, 0.0)
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
    assert q[0] == 0.04 and q[3] == 0.5 and all(0 <= v <= 1 for v in q)


def test_quote_rank_penalizes_memes() -> None:
    useful = {"votos_uteis": 50, "votes_funny": 2, "weighted_vote_score": 0.7}
    meme = {"votos_uteis": 10, "votes_funny": 300, "weighted_vote_score": 0.9}
    assert sorted([meme, useful], key=quote_rank_key)[0] is useful


def _synthetic_scope(seed: int = 0):
    """3 jogos; tema 1 (elogio) sobe a recomendação, tema 2 (reclamação) derruba."""
    rng = random.Random(seed)
    reviews, aspects = [], []
    rid = 0
    for game_id, titulo in ((1, "Hollow Knight"), (2, "Hades"), (3, "Celeste")):
        for _ in range(120):
            rid += 1
            has_praise = rng.random() < 0.35
            has_complaint = rng.random() < 0.25
            p_rec = 0.6 + (0.3 if has_praise else 0) - (0.5 if has_complaint else 0)
            reviews.append(
                {
                    "review_id": rid,
                    "game_id": game_id,
                    "game_titulo": titulo,
                    "recomendada": rng.random() < p_rec,
                    "votos_uteis": rng.randint(0, 100),
                    "votes_funny": 0,
                    "weighted_vote_score": rng.random(),
                    "playtime_at_review": rng.randint(30, 5000),
                    "early_access": False,
                }
            )
            if has_praise:
                aspects.append({"review_id": rid, "theme_id": 1, "trecho": "deep story", "trecho_literal": True})
            if has_complaint:
                aspects.append({"review_id": rid, "theme_id": 2, "trecho": "crashes", "trecho_literal": True})
    themes = {
        1: {"rotulo": "história profunda", "categoria": "historia", "polaridade": "positivo"},
        2: {"rotulo": "travamentos frequentes", "categoria": "performance", "polaridade": "negativo"},
    }
    return reviews, aspects, themes


def test_theme_stats() -> None:
    reviews, aspects, themes = _synthetic_scope()
    stats = {s["theme_id"]: s for s in compute_theme_stats(reviews, aspects, themes)}
    praise, complaint = stats[1], stats[2]
    assert praise["jogos_distintos"] == 3 and len(praise["jogos_exemplo"]) == 3
    assert praise["wilson_low"] <= praise["prevalencia"] <= praise["wilson_high"]
    assert praise["log_odds"] > 0 and complaint["log_odds"] < 0
    assert complaint["significativo"]
    assert len(praise["citacoes"]) == 3
    assert "steamid" not in str(stats)


def test_clustering_separates_groups() -> None:
    rng = np.random.default_rng(0)
    base_a, base_b = np.zeros(384), np.zeros(384)
    base_a[0], base_b[1] = 1, 1
    vectors = np.vstack(
        [base_a + rng.normal(0, 0.02, 384) for _ in range(20)]
        + [base_b + rng.normal(0, 0.02, 384) for _ in range(20)]
        + [rng.normal(0, 1, 384)]
    )
    result = cluster_embeddings(vectors, distance_threshold=0.35, min_cluster_size=5)
    assert len(result.centroids) == 2
    assert len(set(result.labels[:20])) == 1 and len(set(result.labels[20:40])) == 1
    assert result.labels[-1] == NOISE
    assert result.silhouette is not None and result.silhouette > 0.5


def test_drivers_rank_complaint() -> None:
    reviews, aspects, themes = _synthetic_scope()
    matrix = build_driver_matrix(reviews, aspects, themes, min_support=10)
    result = train_drivers(matrix)
    assert result.trained and result.roc_auc is not None and result.roc_auc > 0.5
    complaint = next(d for d in result.drivers if d["feature"] == "tema:2")
    assert complaint["direcao"] == "reduz"
    small = train_drivers(build_driver_matrix(reviews[:50], aspects, themes))
    assert not small.trained


def test_multilabel_validation() -> None:
    a = {1: parse_annotation("gameplay:positivo; historia:negativo"), 2: parse_annotation("nenhum")}
    b = {1: parse_annotation("gameplay:positivo, historia:negativo"), 2: []}
    assert multilabel_kappa(a, b)["kappa_celulas"] == 1.0
    pred = {1: [{"categoria": "gameplay", "sentimento": "positivo"}], 2: []}
    f1 = multilabel_f1(a, pred)
    assert f1["precisao_micro"] == 1.0 and f1["recall_micro"] == 0.5
    assert cohen_kappa(["x", "y"], ["x", "y"]) == 1.0


def test_engine_dashboard() -> None:
    reviews, aspects, themes = _synthetic_scope()
    stats = compute_theme_stats(reviews, aspects, themes, min_mentions=3)
    similar = [
        {"id": 1, "titulo": "Hollow Knight", "pct_positivas": 0.95},
        {"id": 2, "titulo": "Hades", "pct_positivas": 0.98},
    ]
    dash = TriangulationEngine().build(
        pitch={"titulo": "Teste", "descricao": "Metroidvania", "genres": ["Indie"]},
        similar_games=similar,
        similar_stats=stats,
        genre_stats=[{**s, "genero": "Indie"} for s in stats],
        drivers=[],
        reference_reviews=[],
    )
    elogios = dash["destaques"]["elogios"]
    reclamacoes = dash["destaques"]["reclamacoes"]
    # Mesmo tema nos dois escopos → aparece uma vez só (similares têm prioridade)
    assert len(elogios) == 1 and elogios[0]["escopo"] == "similares"
    assert "Hollow Knight" in elogios[0]["frase"] or "Hades" in elogios[0]["frase"]
    assert reclamacoes[0]["tema"]["polaridade"] == "negativo"
    empty = TriangulationEngine().build(
        pitch={}, similar_games=[], similar_stats=[], genre_stats=[], drivers=[], reference_reviews=[]
    )
    assert empty["alertas"][0]["tipo"] == "dados_insuficientes"


if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]
    for test in tests:
        test()
        print(f"  ✓ {test.__name__}")
    print(f"✅ {len(tests)} testes sintéticos OK")
