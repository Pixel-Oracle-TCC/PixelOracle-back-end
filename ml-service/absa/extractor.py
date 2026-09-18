"""Extração ABSA (aspecto + sentimento) via Gemini em lotes."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

FEW_SHOT_PROMPT = """Você extrai aspectos e sentimento de reviews de jogos Steam.
Para cada review, retorne APENAS um JSON array. Cada item:
{{"recommendationid": "...", "aspecto": "gameplay|historia|graficos|preco|performance|multiplayer|conteudo|outros", "sentimento": "positivo|negativo|neutro"}}

Exemplos:
Review: "Combate fluido mas a história é genérica." → aspecto gameplay positivo; se houver um único rótulo, escolha o aspecto dominante.
Review: "Jogo travando no notebook fraco." → performance / negativo

Reviews:
{reviews_block}

Responda só o JSON array.
"""


class AbsaExtractor:
    """Extração few-shot via Gemini. Idempotente no nível de chamada (sem side-effect)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        sleep_seconds: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.sleep_seconds = sleep_seconds

    def extract_batch(
        self, reviews: List[Dict[str, Any]], batch_size: int = 10
    ) -> List[Dict[str, str]]:
        """
        reviews: lista com recommendationid + texto.
        Retorna lista de {recommendationid, aspecto, sentimento}.
        """
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada para ABSA.")

        outputs: List[Dict[str, str]] = []
        for i in range(0, len(reviews), batch_size):
            chunk = reviews[i : i + batch_size]
            parsed = self._call_gemini(chunk)
            outputs.extend(parsed)
            time.sleep(self.sleep_seconds)
            logger.info("ABSA progresso: %s/%s", min(i + batch_size, len(reviews)), len(reviews))
        return outputs

    def _call_gemini(self, chunk: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        lines = []
        for item in chunk:
            rid = item.get("recommendationid", "")
            text = (item.get("texto") or "")[:800].replace("\n", " ")
            lines.append(f"[{rid}] {text}")
        prompt = FEW_SHOT_PROMPT.format(reviews_block="\n".join(lines))

        url = GEMINI_GENERATE_URL.format(model=self.model)
        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return self._parse_json_array(text)
        except requests.RequestException as exc:
            logger.error("Falha Gemini ABSA: %s", exc)
            raise

    @staticmethod
    def _parse_json_array(text: str) -> List[Dict[str, str]]:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            logger.warning("Resposta Gemini sem JSON array: %s", text[:200])
            return []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("JSON ABSA inválido")
            return []
        results: List[Dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("recommendationid") or "")
            aspecto = str(item.get("aspecto") or "outros").lower()
            sentimento = str(item.get("sentimento") or "neutro").lower()
            if rid:
                results.append(
                    {
                        "recommendationid": rid,
                        "aspecto": aspecto,
                        "sentimento": sentimento,
                    }
                )
        return results
