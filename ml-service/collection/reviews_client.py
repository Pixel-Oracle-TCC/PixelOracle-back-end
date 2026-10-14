"""Cliente de reviews Steam (IUserReviewsService/GetAppReviews).

Conformidade (obrigatória — ToS Steam Cláusula 2 + LGPD):
- Nunca persiste author.steamid nem qualquer identificador de usuário.
- Deduplica por recommendationid (nunca por steamid).
- Persona de público = agregação por GÊNERO/tema, não por indivíduo.

O endpoint store.steampowered.com/appreviews está depreciado; usamos GetAppReviews e só
caímos no legado se o novo falhar (ex.: mudança de rota ou bloqueio).
A Steam NÃO expõe awards na API — relevância vem de votes_up + weighted_vote_score.
Não fazer scraping do HTML da loja para obter awards (risco de ToS).

Ver vault: [[Conformidade Steam e LGPD]] / [[Coleta de Reviews]].
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

import requests

logger = logging.getLogger(__name__)

GET_APP_REVIEWS_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
LEGACY_APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"

# Enums de IUserReviewsService
FILTER_HELPFUL = 0
FILTER_RECENT = 1
REVIEW_TYPE_ALL = 0
REVIEW_TYPE_POSITIVE = 1
REVIEW_TYPE_NEGATIVE = 2
PURCHASE_TYPE_ALL = 1

_LEGACY_FILTER = {FILTER_HELPFUL: "all", FILTER_RECENT: "recent"}
_LEGACY_REVIEW_TYPE = {
    REVIEW_TYPE_ALL: "all",
    REVIEW_TYPE_POSITIVE: "positive",
    REVIEW_TYPE_NEGATIVE: "negative",
}

SampleType = Literal["util_positiva", "util_negativa", "recente"]

DEFAULT_LANGUAGES = ("brazilian", "english")
MAX_TEXT_CHARS = 4000


@dataclass
class GameReviewSample:
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    # query_summary: total_positive, total_negative, total_reviews, review_score_desc
    summary: Dict[str, Any] = field(default_factory=dict)


class ReviewsClient:
    """Coleta reviews públicas sem dados de perfil do autor."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        sleep_seconds: float = 1.5,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or None
        self.timeout = timeout
        # Sleep explícito entre páginas: respeita o rate limit compartilhado sem chave
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries
        self._use_legacy = False
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )

    def collect_sample(
        self,
        appid: int,
        *,
        helpful_positive: int = 40,
        helpful_negative: int = 40,
        recent: int = 20,
        languages: Sequence[str] = DEFAULT_LANGUAGES,
    ) -> GameReviewSample:
        """
        Três fatias por jogo:
        - mais úteis positivas e negativas de todos os tempos (Helpful, day_range=0,
          use_review_quality=true → a Steam já rebaixa memes, ASCII art e off-topic);
        - recentes (estado atual do jogo). A 1ª página dela traz o query_summary.

        Fatias positivas/negativas separadas: sem isso a amostra fica dominada pela
        polaridade majoritária do jogo e as reclamações somem.
        """
        sample = GameReviewSample()
        seen: set[str] = set()

        slices = [
            ("recente", FILTER_RECENT, REVIEW_TYPE_ALL, recent),
            ("util_positiva", FILTER_HELPFUL, REVIEW_TYPE_POSITIVE, helpful_positive),
            ("util_negativa", FILTER_HELPFUL, REVIEW_TYPE_NEGATIVE, helpful_negative),
        ]
        for tipo, filter_value, review_type, limit in slices:
            if limit <= 0 and review_type != REVIEW_TYPE_ALL:
                continue
            raw_reviews, summary = self._collect_slice(
                appid,
                filter_value=filter_value,
                review_type=review_type,
                limit=max(limit, 1),
                languages=languages,
            )
            if summary and not sample.summary:
                sample.summary = summary
            taken = 0
            for raw in raw_reviews:
                if taken >= limit:
                    break
                sanitized = self.sanitize_review(raw, tipo_amostra=tipo)  # type: ignore[arg-type]
                if sanitized is None:
                    continue
                rid = sanitized["recommendationid"]
                # Dedup entre fatias (a mesma review pode ser útil e recente)
                if rid in seen:
                    continue
                if languages and sanitized["language"] not in languages:
                    continue
                seen.add(rid)
                sample.reviews.append(sanitized)
                taken += 1
        return sample

    def _collect_slice(
        self,
        appid: int,
        *,
        filter_value: int,
        review_type: int,
        limit: int,
        languages: Sequence[str],
        max_pages: int = 10,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        summary: Dict[str, Any] = {}
        cursor = "*"
        for page in range(max_pages):
            payload = self.fetch_page(
                appid,
                filter_value=filter_value,
                review_type=review_type,
                languages=languages,
                cursor=cursor,
                num_per_page=min(100, max(limit - len(collected), 20)),
            )
            if page == 0:
                summary = self._extract_summary(payload.get("query_summary") or {})
            reviews = payload.get("reviews") or []
            collected.extend(reviews)
            next_cursor = payload.get("cursor")
            if not reviews or not next_cursor or next_cursor == cursor or len(collected) >= limit:
                break
            cursor = next_cursor
        return collected, summary

    def fetch_page(
        self,
        appid: int,
        *,
        filter_value: int,
        review_type: int,
        languages: Sequence[str],
        cursor: str = "*",
        num_per_page: int = 100,
    ) -> Dict[str, Any]:
        if not self._use_legacy:
            try:
                return self._fetch_service(
                    appid, filter_value, review_type, languages, cursor, num_per_page
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (400, 403, 404, 405):
                    logger.warning(
                        "GetAppReviews indisponível (HTTP %s) — usando appreviews legado.", status
                    )
                    self._use_legacy = True
                else:
                    raise
        return self._fetch_legacy(appid, filter_value, review_type, cursor, num_per_page)

    def _fetch_service(
        self,
        appid: int,
        filter_value: int,
        review_type: int,
        languages: Sequence[str],
        cursor: str,
        num_per_page: int,
    ) -> Dict[str, Any]:
        input_json: Dict[str, Any] = {
            "appid": int(appid),
            "filter": filter_value,
            "review_type": review_type,
            "purchase_type": PURCHASE_TYPE_ALL,
            "languages": list(languages) or ["all"],
            "cursor": cursor,
            "num_per_page": num_per_page,
        }
        if filter_value == FILTER_HELPFUL:
            # day_range=0 → sem limite: "mais úteis de todos os tempos"
            input_json["day_range"] = 0
            input_json["use_review_quality"] = True
        params: Dict[str, Any] = {"input_json": json.dumps(input_json)}
        if self.api_key:
            params["key"] = self.api_key
        data = self._get_with_retry(GET_APP_REVIEWS_URL, params)
        # Interfaces de serviço embrulham a resposta em {"response": {...}}
        return data.get("response", data)

    def _fetch_legacy(
        self,
        appid: int,
        filter_value: int,
        review_type: int,
        cursor: str,
        num_per_page: int,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "json": 1,
            "filter": _LEGACY_FILTER[filter_value],
            "review_type": _LEGACY_REVIEW_TYPE[review_type],
            "purchase_type": "all",
            "num_per_page": num_per_page,
            # Legado só aceita um idioma; filtramos por idioma depois, em collect_sample
            "language": "all",
            "cursor": cursor,
        }
        if filter_value == FILTER_HELPFUL:
            params["day_range"] = 365
        return self._get_with_retry(LEGACY_APPREVIEWS_URL.format(appid=appid), params)

    def _get_with_retry(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 429:
                    wait = self.sleep_seconds * (2**attempt)
                    logger.warning("Rate limit (429). Aguardando %.1fs", wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.HTTPError:
                raise
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(self.sleep_seconds * attempt)
            finally:
                time.sleep(self.sleep_seconds)
        raise RuntimeError(f"Falha ao consultar {url}: {last_exc}")

    @staticmethod
    def _extract_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        keys = ("total_positive", "total_negative", "total_reviews", "review_score_desc")
        return {k: raw[k] for k in keys if k in raw}

    @staticmethod
    def sanitize_review(
        raw: Dict[str, Any], *, tipo_amostra: SampleType
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai campos permitidos e DESCARTA author (incl. steamid).

        IMPORTANTE PARA O SQUAD:
        - A resposta da Steam traz `author.steamid`. Só lemos playtime_at_review
          em memória; o dict de saída NUNCA inclui steamid/author.
        - developer_response é texto público do estúdio, não dado pessoal do jogador.
        - Sem recommendationid → descarta (não dá para deduplicar com segurança).
        """
        recommendationid = raw.get("recommendationid")
        if not recommendationid:
            return None

        author = raw.get("author") or {}
        # NÃO fazer: return {..., "author": raw["author"]}
        # NÃO fazer: author.get("steamid")
        return {
            "recommendationid": str(recommendationid),
            "texto": (raw.get("review") or "")[:MAX_TEXT_CHARS],
            "recomendada": bool(raw.get("voted_up")),
            "votos_uteis": _as_int(raw.get("votes_up")),
            "votes_funny": _as_int(raw.get("votes_funny")),
            "weighted_vote_score": _as_float(raw.get("weighted_vote_score")),
            "comment_count": _as_int(raw.get("comment_count")),
            "playtime_at_review": _as_int(author.get("playtime_at_review")),
            "language": raw.get("language"),
            "timestamp_created": _as_int(raw.get("timestamp_created")) or None,
            "early_access": bool(raw.get("written_during_early_access")),
            "steam_purchase": bool(raw.get("steam_purchase")),
            "developer_response": raw.get("developer_response") or None,
            "timestamp_dev_responded": _as_int(raw.get("timestamp_dev_responded")) or None,
            "tipo_amostra": tipo_amostra,
        }


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> Optional[float]:
    # No legado weighted_vote_score vem como string
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
