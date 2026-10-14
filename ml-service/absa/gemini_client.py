"""Cliente REST mínimo da Gemini para tarefas offline (ABSA e nomeação de temas).

Usa responseMimeType=application/json e temperature=0: as tarefas são de extração,
não de criatividade, e a saída precisa ser parseável e reprodutível.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiQuotaExceeded(RuntimeError):
    """Cota diária esgotada: repetir não adianta até o reset (free tier: 20 req/dia/modelo)."""


def _is_daily_quota(response: requests.Response) -> bool:
    try:
        details = response.json().get("error", {}).get("details", [])
    except ValueError:
        return False
    for detail in details:
        for violation in detail.get("violations", []) or []:
            if "PerDay" in str(violation.get("quotaId", "")):
                return True
    return False


class GeminiJsonClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 90.0,
        max_retries: int = 3,
        thinking_budget: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout
        self.max_retries = max_retries
        # Extração não precisa de raciocínio longo: com o padrão do 2.5-flash um lote de
        # 10 reviews leva ~40s; com 0 cai para poucos segundos. Vazio = padrão do modelo.
        if thinking_budget is None:
            raw = os.getenv("GEMINI_THINKING_BUDGET", "0").strip()
            thinking_budget = int(raw) if raw else None
        self.thinking_budget = thinking_budget

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate_json(self, prompt: str) -> Any:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada.")
        url = GEMINI_GENERATE_URL.format(model=self.model)
        generation_config: dict = {
            "temperature": 0,
            "responseMimeType": "application/json",
        }
        if self.thinking_budget is not None:
            generation_config["thinkingConfig"] = {"thinkingBudget": self.thinking_budget}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    url, params={"key": self.api_key}, json=body, timeout=self.timeout
                )
                if response.status_code == 429 and _is_daily_quota(response):
                    raise GeminiQuotaExceeded(
                        f"Cota diária da Gemini esgotada para {self.model}. "
                        "Tente após o reset ou use outro GEMINI_MODEL."
                    )
                if response.status_code in (429, 500, 503):
                    wait = 2 ** attempt * 2
                    logger.warning("Gemini HTTP %s — nova tentativa em %ss", response.status_code, wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return parse_json_payload(text)
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                time.sleep(2 * attempt)
        raise RuntimeError(f"Falha na Gemini após {self.max_retries} tentativas: {last_exc}")


def parse_json_payload(text: str) -> Any:
    """Aceita JSON puro ou embrulhado em markdown (```json ... ```)."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if not match:
            raise ValueError(f"Resposta sem JSON: {text[:200]}")
        return json.loads(match.group(0))
