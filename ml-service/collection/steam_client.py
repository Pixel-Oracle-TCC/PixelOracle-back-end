"""Cliente Steam Web API — metadados de jogos (não dados de usuários)."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

STEAM_STORE_APPDETAILS = "https://store.steampowered.com/api/appdetails"
STEAM_WEEKLY_TOP_SELLERS = (
    "https://api.steampowered.com/IStoreTopSellersService/GetWeeklyTopSellers/v1/"
)

# Store bloqueia User-Agent padrão do requests com ConnectionReset
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


class SteamClient:
    """Consome top sellers e appdetails. Escopo: dados de jogos, não de perfis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        sleep_seconds: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("STEAM_API_KEY", "")
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def get_weekly_top_sellers(
        self, start_date: Optional[int] = None, country: str = "BR", language: str = "brazilian"
    ) -> Dict[str, Any]:
        """
        Top 100 por receita da semana iniciada em `start_date` (unix; None = semana atual).
        Retorna {"start_date": int, "ranks": [{"rank", "appid", "item": {...}}, ...]}.
        A API entrega no máximo 100 posições por semana; o histórico vai até 2016.
        """
        payload: Dict[str, Any] = {
            "country_code": country,
            "context": {"language": language, "country_code": country},
            "page_start": 0,
            "page_count": 100,
        }
        if start_date is not None:
            payload["start_date"] = int(start_date)
        params: Dict[str, Any] = {"input_json": json.dumps(payload)}
        if self.api_key:
            params["key"] = self.api_key
        try:
            response = self._session.get(
                STEAM_WEEKLY_TOP_SELLERS, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("response") or {}
        except (requests.RequestException, ValueError) as exc:
            logger.error("Falha GetWeeklyTopSellers start_date=%s: %s", start_date, exc)
            raise

    def get_app_details(
        self, appid: int, country: str = "BR", language: str = "brazilian"
    ) -> Optional[Dict[str, Any]]:
        """Retorna o bloco data de appdetails ou None se indisponível."""
        params = {"appids": appid, "cc": country, "l": language}
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(
                    STEAM_STORE_APPDETAILS, params=params, timeout=self.timeout
                )
                response.raise_for_status()
                payload = response.json()
                entry = payload.get(str(appid), {})
                time.sleep(self.sleep_seconds)
                if not entry.get("success"):
                    return None
                return entry.get("data")
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                wait = self.sleep_seconds * attempt
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status == 429:
                    # Store: ~200 appdetails a cada 5 min por IP
                    wait = 60.0 * attempt
                elif isinstance(exc, requests.ConnectionError):
                    # Rajadas levam a Store a derrubar a conexão; a sessão reaproveitada continua bloqueada
                    wait = 20.0 * attempt
                    self._session = requests.Session()
                    self._session.headers.update(DEFAULT_HEADERS)
                logger.warning(
                    "appdetails appid=%s tentativa %s/%s falhou: %s — retry em %.1fs",
                    appid,
                    attempt,
                    self.max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        logger.error("Falha appdetails appid=%s: %s", appid, last_exc)
        if last_exc:
            raise last_exc
        return None

    @staticmethod
    def extract_price_brl(data: Dict[str, Any]) -> Optional[float]:
        overview = data.get("price_overview") or {}
        final = overview.get("final")
        if final is None:
            return 0.0 if data.get("is_free") else None
        return float(final) / 100.0

    @staticmethod
    def extract_release_year(data: Dict[str, Any]) -> Optional[int]:
        date_str = (data.get("release_date") or {}).get("date") or ""
        digits = "".join(ch if ch.isdigit() else " " for ch in date_str).split()
        years = [int(x) for x in digits if len(x) == 4 and x.startswith("20")]
        return years[-1] if years else None
