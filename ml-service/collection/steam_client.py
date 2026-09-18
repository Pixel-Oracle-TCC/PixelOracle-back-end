"""Cliente Steam Web API — metadados de jogos (não dados de usuários)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

STEAM_STORE_APPDETAILS = "https://store.steampowered.com/api/appdetails"
STEAM_GET_APP_LIST = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

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
    """Consome GetAppList e appdetails. Escopo: dados de jogos, não de perfis."""

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

    def get_app_list(self) -> List[Dict[str, Any]]:
        """Lista appid + name de todos os apps Steam (pode ser grande)."""
        try:
            response = self._session.get(STEAM_GET_APP_LIST, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            return payload.get("applist", {}).get("apps", [])
        except requests.RequestException as exc:
            logger.error("Falha GetAppList: %s", exc)
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
