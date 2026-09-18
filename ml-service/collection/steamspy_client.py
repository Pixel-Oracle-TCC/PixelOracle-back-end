"""Cliente SteamSpy — owners estimados agregados (não vinculados a indivíduo)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

STEAMSPY_APP_URL = "https://steamspy.com/api.php"


class SteamSpyClient:
    """Consulta owners estimados por appid."""

    def __init__(self, timeout: float = 30.0, sleep_seconds: float = 1.0) -> None:
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self._session = requests.Session()

    def get_app_details(self, appid: int) -> Optional[Dict[str, Any]]:
        params = {"request": "appdetails", "appid": appid}
        try:
            response = self._session.get(
                STEAMSPY_APP_URL, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if not data or data.get("appid") is None:
                return None
            return data
        except requests.RequestException as exc:
            logger.error("Falha SteamSpy appid=%s: %s", appid, exc)
            raise
        finally:
            time.sleep(self.sleep_seconds)

    @staticmethod
    def parse_owners_midpoint(owners_field: Optional[str]) -> Optional[int]:
        """
        SteamSpy retorna faixas como '100,000 .. 200,000'.
        Usa o ponto médio da faixa como estimativa agregada.
        """
        if not owners_field or not isinstance(owners_field, str):
            return None
        cleaned = owners_field.replace(",", "").replace(" ", "")
        if ".." not in cleaned:
            try:
                return int(cleaned)
            except ValueError:
                return None
        left, right = cleaned.split("..", 1)
        try:
            low, high = int(left), int(right)
            return (low + high) // 2
        except ValueError:
            return None
