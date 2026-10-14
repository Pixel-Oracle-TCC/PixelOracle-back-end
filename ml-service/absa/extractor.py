"""Extração ABSA multi-aspecto (categoria + sentimento + trecho + resumo) via Gemini.

Cada review pode ter vários aspectos: "combate fluido, mas a história é genérica" gera
gameplay/positivo e historia/negativo. O trecho é uma citação literal (evidência exibida
no dashboard); o resumo é uma paráfrase curta em português usada para agrupar temas,
o que deixa reviews em inglês e português no mesmo espaço semântico.

A Gemini aqui EXTRAI, não opina. A qualidade é medida contra o gold standard
(Kappa entre anotadores + F1 Gemini vs consenso) — ver absa/validation.py.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

from absa.gemini_client import GeminiJsonClient, GeminiQuotaExceeded
from absa.taxonomy import CATEGORIES, normalize_category, normalize_sentiment

logger = logging.getLogger(__name__)

MAX_REVIEW_CHARS = 1500

_CATEGORY_LINES = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())

PROMPT_TEMPLATE = """Você extrai aspectos de reviews de jogos da Steam.

Categorias permitidas:
{categories}

Para CADA review, liste todos os aspectos mencionados (0 a 5). Para cada aspecto:
- "categoria": uma das categorias acima
- "sentimento": "positivo", "negativo" ou "neutro"
- "trecho": cópia LITERAL de uma parte curta da review (até 25 palavras) que sustenta o aspecto, no idioma original
- "resumo": paráfrase em português de 3 a 8 palavras, genérica o bastante para agrupar opiniões parecidas (ex.: "história profunda e emocionante", "travamentos frequentes no PC")

Não invente aspectos que não estão no texto. Reviews só com piada ou sem opinião sobre o jogo → lista vazia.

Exemplo:
Review [1]: "Combat feels amazing but the story is forgettable."
→ {{"id": "1", "aspectos": [
  {{"categoria": "gameplay", "sentimento": "positivo", "trecho": "Combat feels amazing", "resumo": "combate fluido e satisfatório"}},
  {{"categoria": "historia", "sentimento": "negativo", "trecho": "the story is forgettable", "resumo": "história genérica e esquecível"}}
]}}

Reviews:
{reviews_block}

Responda APENAS um JSON array: [{{"id": "...", "aspectos": [...]}}, ...]
"""


def is_literal_excerpt(trecho: str, texto: str) -> bool:
    """O trecho existe no texto? (ignora caixa e espaços). Falso → não vira citação."""
    if not trecho or not texto:
        return False
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()  # noqa: E731
    return norm(trecho) in norm(texto)


class AbsaExtractor:
    """Extração em lote. Idempotente no nível de chamada (sem side-effect no banco)."""

    def __init__(
        self,
        client: Optional[GeminiJsonClient] = None,
        sleep_seconds: float = 1.0,
    ) -> None:
        self.client = client or GeminiJsonClient()
        self.sleep_seconds = sleep_seconds
        self.quota_exhausted = False

    @property
    def model_name(self) -> str:
        budget = getattr(self.client, "thinking_budget", None)
        return self.client.model if budget is None else f"{self.client.model}@thinking={budget}"

    def extract_batch(
        self, reviews: List[Dict[str, Any]], batch_size: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        reviews: dicts com "recommendationid" e "texto".
        Retorna {recommendationid: [aspectos]}; reviews que falharam ficam fora do dict
        (o script não as marca como processadas e tenta de novo depois).
        """
        results: Dict[str, List[Dict[str, Any]]] = {}
        for i in range(0, len(reviews), batch_size):
            chunk = reviews[i : i + batch_size]
            try:
                results.update(self._extract_chunk(chunk))
            except GeminiQuotaExceeded as exc:
                logger.error("%s", exc)
                self.quota_exhausted = True
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Lote ABSA falhou (%s reviews): %s", len(chunk), exc)
            time.sleep(self.sleep_seconds)
            logger.info("ABSA progresso: %s/%s", min(i + batch_size, len(reviews)), len(reviews))
        return results

    def _extract_chunk(self, chunk: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        # IDs curtos no prompt (1..n): recommendationid longo confunde o modelo
        by_local_id = {str(n): item for n, item in enumerate(chunk, start=1)}
        lines = [
            f"Review [{local_id}]: {(item.get('texto') or '')[:MAX_REVIEW_CHARS]!r}"
            for local_id, item in by_local_id.items()
        ]
        prompt = PROMPT_TEMPLATE.format(categories=_CATEGORY_LINES, reviews_block="\n".join(lines))
        parsed = self.client.generate_json(prompt)
        if not isinstance(parsed, list):
            raise ValueError("Resposta ABSA não é um array.")

        output: Dict[str, List[Dict[str, Any]]] = {}
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            item = by_local_id.get(str(entry.get("id")))
            if item is None:
                continue
            output[str(item["recommendationid"])] = self._clean_aspects(
                entry.get("aspectos") or [], item.get("texto") or ""
            )
        # Reviews omitidas pelo modelo contam como "sem aspectos" (não reprocessa à toa)
        for item in chunk:
            output.setdefault(str(item["recommendationid"]), [])
        return output

    @staticmethod
    def _clean_aspects(raw_aspects: List[Any], texto: str) -> List[Dict[str, Any]]:
        cleaned: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for raw in raw_aspects[:5]:
            if not isinstance(raw, dict):
                continue
            categoria = normalize_category(str(raw.get("categoria") or ""))
            sentimento = normalize_sentiment(str(raw.get("sentimento") or ""))
            trecho = str(raw.get("trecho") or "").strip()[:400]
            resumo = str(raw.get("resumo") or "").strip()[:120]
            key = (categoria, sentimento, resumo.lower())
            if not resumo or key in seen:
                continue
            seen.add(key)
            cleaned.append(
                {
                    "categoria": categoria,
                    "sentimento": sentimento,
                    "trecho": trecho or None,
                    "trecho_literal": is_literal_excerpt(trecho, texto),
                    "resumo": resumo,
                }
            )
        return cleaned
