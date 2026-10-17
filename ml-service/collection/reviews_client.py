"""Cliente de reviews Steam (IUserReviewsService/GetAppReviews).

Conformidade (obrigatória — ToS Steam Cláusula 2 + LGPD):
- Nunca persiste author.steamid nem qualquer identificador de usuário.
- Deduplica por recommendationid (nunca por steamid).
- Persona de público = agregação por GÊNERO/tema, não por indivíduo.

Fatias: uma review pode pertencer a várias (`fatias TEXT[]`). Não há dedup entre
fatias — se uma review recente também é útil, fica em ambas. Métricas usam só
`proporcional`; úteis servem para citações.

A fatia proporcional usa filter=recent (últimas semanas), não a vida inteira do
jogo — documentado no TCC / vault.

Ver vault: [[Conformidade Steam e LGPD]] / [[Coleta de Reviews]].
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Set

import requests

logger = logging.getLogger(__name__)

GET_APP_REVIEWS_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
LEGACY_APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"

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

SampleType = Literal["util_positiva", "util_negativa", "proporcional"]
FATIA_PROPORCIONAL = "proporcional"
FATIAS_UTEIS = frozenset({"util_positiva", "util_negativa"})

DEFAULT_LANGUAGES = ("brazilian", "english")
MAX_TEXT_CHARS = 4000
MIN_TEXT_CHARS = 20

# Defaults: proporcional por idioma (PT+EN ≈ 100); úteis menores (citações)
DEFAULT_PROPORTIONAL_PER_LANGUAGE = 50
DEFAULT_HELPFUL_POSITIVE = 25
DEFAULT_HELPFUL_NEGATIVE = 25


@dataclass
class GameReviewSample:
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    summary_unfiltered: Dict[str, Any] = field(default_factory=dict)


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

    def fetch_summary(
        self, appid: int, *, filter_offtopic_activity: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Só query_summary (num_per_page=0). Usado no enrich/select e no snapshot dual."""
        input_json: Dict[str, Any] = {
            "appid": int(appid),
            "filter": FILTER_RECENT,
            "review_type": REVIEW_TYPE_ALL,
            "purchase_type": PURCHASE_TYPE_ALL,
            "languages": ["all"],
            "cursor": "*",
            "num_per_page": 0,
        }
        if filter_offtopic_activity is not None:
            input_json["filter_offtopic_activity"] = bool(filter_offtopic_activity)
        params: Dict[str, Any] = {"input_json": json.dumps(input_json)}
        if self.api_key:
            params["key"] = self.api_key
        try:
            data = self._get_with_retry(GET_APP_REVIEWS_URL, params)
            payload = data.get("response", data)
            return self._extract_summary(payload.get("query_summary") or {})
        except Exception:  # noqa: BLE001 — fallback legado
            params_legacy: Dict[str, Any] = {
                "json": 1,
                "filter": "all",
                "language": "all",
                "num_per_page": 0,
                "purchase_type": "all",
            }
            if filter_offtopic_activity is not None:
                params_legacy["filter_offtopic_activity"] = int(bool(filter_offtopic_activity))
            data = self._get_with_retry(LEGACY_APPREVIEWS_URL.format(appid=appid), params_legacy)
            return self._extract_summary(data.get("query_summary") or {})

    def collect_sample(
        self,
        appid: int,
        *,
        helpful_positive: int = DEFAULT_HELPFUL_POSITIVE,
        helpful_negative: int = DEFAULT_HELPFUL_NEGATIVE,
        proportional_per_language: int = DEFAULT_PROPORTIONAL_PER_LANGUAGE,
        languages: Sequence[str] = DEFAULT_LANGUAGES,
    ) -> GameReviewSample:
        """
        Fatias por jogo (limites contam só após filtro de qualidade):
        - proporcional: recentes sem filtro de tipo, **por idioma** (default 50×2);
        - util_positiva / util_negativa: mais úteis de todos os tempos (default 25 cada).

        Sem dedup entre fatias: a mesma review pode entrar em várias; `fatias` acumula.
        """
        sample = GameReviewSample()
        by_rid: Dict[str, Dict[str, Any]] = {}
        # near-dup por fatia+idioma: texto normalizado
        seen_norm: Dict[str, Set[str]] = defaultdict(set)

        sample.summary = self.fetch_summary(appid, filter_offtopic_activity=True)
        sample.summary_unfiltered = self.fetch_summary(appid, filter_offtopic_activity=False)

        # Proporcional por idioma (confirma: o limite é POR idioma, não no total)
        for lang in languages:
            self._fill_slice(
                by_rid,
                seen_norm,
                appid,
                tipo=FATIA_PROPORCIONAL,
                filter_value=FILTER_RECENT,
                review_type=REVIEW_TYPE_ALL,
                limit=proportional_per_language,
                languages=(lang,),
            )

        for tipo, review_type, limit in (
            ("util_positiva", REVIEW_TYPE_POSITIVE, helpful_positive),
            ("util_negativa", REVIEW_TYPE_NEGATIVE, helpful_negative),
        ):
            if limit <= 0:
                continue
            self._fill_slice(
                by_rid,
                seen_norm,
                appid,
                tipo=tipo,  # type: ignore[arg-type]
                filter_value=FILTER_HELPFUL,
                review_type=review_type,
                limit=limit,
                languages=languages,
            )

        sample.reviews = list(by_rid.values())
        return sample

    def _fill_slice(
        self,
        by_rid: Dict[str, Dict[str, Any]],
        seen_norm: Dict[str, Set[str]],
        appid: int,
        *,
        tipo: SampleType,
        filter_value: int,
        review_type: int,
        limit: int,
        languages: Sequence[str],
        max_pages: int = 20,
    ) -> None:
        if limit <= 0:
            return
        taken = 0
        cursor = "*"
        for _page in range(max_pages):
            if taken >= limit:
                break
            payload = self.fetch_page(
                appid,
                filter_value=filter_value,
                review_type=review_type,
                languages=languages,
                cursor=cursor,
                num_per_page=min(100, max(limit - taken, 20)),
            )
            reviews = payload.get("reviews") or []
            if not reviews:
                break
            for raw in reviews:
                if taken >= limit:
                    break
                sanitized = self.sanitize_review(raw, fatia=tipo)
                if sanitized is None:
                    continue
                if languages and sanitized["language"] not in languages:
                    continue
                if not is_usable_review_text(sanitized["texto"]):
                    continue
                norm = normalize_review_text(sanitized["texto"])
                dup_key = f"{tipo}:{sanitized.get('language') or ''}"
                if norm in seen_norm[dup_key]:
                    continue
                rid = sanitized["recommendationid"]
                if rid in by_rid:
                    fatias = by_rid[rid]["fatias"]
                    if tipo not in fatias:
                        fatias.append(tipo)
                else:
                    by_rid[rid] = sanitized
                seen_norm[dup_key].add(norm)
                taken += 1
            next_cursor = payload.get("cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

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
            input_json["day_range"] = 0
            input_json["use_review_quality"] = True
        params: Dict[str, Any] = {"input_json": json.dumps(input_json)}
        if self.api_key:
            params["key"] = self.api_key
        data = self._get_with_retry(GET_APP_REVIEWS_URL, params)
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
        keys = (
            "total_positive",
            "total_negative",
            "total_reviews",
            "review_score",
            "review_score_desc",
        )
        return {k: raw[k] for k in keys if k in raw}

    @staticmethod
    def sanitize_review(
        raw: Dict[str, Any], *, fatia: SampleType
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai campos permitidos e DESCARTA author (incl. steamid).

        Saída inclui `fatias` (lista com a fatia atual). O caller une fatias no UPSERT.
        """
        recommendationid = raw.get("recommendationid")
        if not recommendationid:
            return None

        author = raw.get("author") or {}
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
            "received_for_free": bool(raw.get("received_for_free")),
            "developer_response": raw.get("developer_response") or None,
            "timestamp_dev_responded": _as_int(raw.get("timestamp_dev_responded")) or None,
            "fatias": [fatia],
        }


def is_usable_review_text(texto: Optional[str]) -> bool:
    """Descarta lixo antes de contar a cota da fatia (<20 chars, só pontuação, ASCII art)."""
    if not texto:
        return False
    t = texto.strip()
    if len(t) < MIN_TEXT_CHARS:
        return False
    alnum = sum(1 for c in t if c.isalnum())
    if alnum < 12:
        return False
    # ASCII art / spam de símbolos: poucos caracteres de palavra
    letters = sum(1 for c in t if c.isalpha())
    if letters < 10:
        return False
    if letters / max(len(t), 1) < 0.35:
        return False
    return True


def normalize_review_text(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").strip().lower())


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
