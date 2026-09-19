"""Cliente de reviews Steam (appreviews).

Conformidade (obrigatória — ToS Steam Cláusula 2 + LGPD):
- Nunca persiste author.steamid nem qualquer identificador de usuário.
- Deduplica por recommendationid (nunca por steamid).
- Persona de público = agregação por GÊNERO (genre_insights), não por indivíduo.

Ver vault: [[Conformidade Steam e LGPD]].
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Literal, Optional

import requests

logger = logging.getLogger(__name__)

APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"

SampleType = Literal["positiva", "negativa", "recente"]


class ReviewsClient:
    """Coleta reviews públicas sem dados de perfil do autor."""

    def __init__(self, timeout: float = 30.0, sleep_seconds: float = 1.5) -> None:
        self.timeout = timeout
        # Sleep explícito: respeita rate limit da Store (não confiar só na "sorte")
        self.sleep_seconds = sleep_seconds
        self._session = requests.Session()

    def fetch_reviews(
        self,
        appid: int,
        *,
        filter_type: str = "all",
        review_type: str = "all",
        num_per_page: int = 20,
        language: str = "all",
        cursor: str = "*",
    ) -> Dict[str, Any]:
        params = {
            "json": 1,
            "filter": filter_type,
            "review_type": review_type,
            "purchase_type": "all",
            "num_per_page": num_per_page,
            "language": language,
            "cursor": cursor,
        }
        url = APPREVIEWS_URL.format(appid=appid)
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("Falha appreviews appid=%s: %s", appid, exc)
            raise
        finally:
            time.sleep(self.sleep_seconds)

    def collect_sample(
        self,
        appid: int,
        *,
        positive_limit: int = 10,
        negative_limit: int = 10,
        recent_limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Coleta top positivas, negativas e recentes.
        Retorna registros já sanitizados (sem author/steamid).

        Por quê três fatias: equilíbrio para ABSA (não só reviews entusiastas).
        """
        seen: set[str] = set()
        results: List[Dict[str, Any]] = []

        batches = [
            ("positiva", "all", "positive", positive_limit),
            ("negativa", "all", "negative", negative_limit),
            ("recente", "recent", "all", recent_limit),
        ]

        for tipo, filter_type, review_type, limit in batches:
            if limit <= 0:
                continue
            payload = self.fetch_reviews(
                appid,
                filter_type=filter_type,
                review_type=review_type,
                num_per_page=min(limit, 100),
            )
            for raw in payload.get("reviews") or []:
                sanitized = self.sanitize_review(raw, tipo_amostra=tipo)  # type: ignore[arg-type]
                if sanitized is None:
                    continue
                rid = sanitized["recommendationid"]
                # Dedup entre fatias (a mesma review pode aparecer em "recente" e "positiva")
                if rid in seen:
                    continue
                seen.add(rid)
                results.append(sanitized)
                if sum(1 for r in results if r["tipo_amostra"] == tipo) >= limit:
                    break

        return results

    @staticmethod
    def sanitize_review(
        raw: Dict[str, Any], *, tipo_amostra: SampleType
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai campos permitidos e DESCARTA author (incl. steamid).

        IMPORTANTE PARA O SQUAD:
        - A resposta da Steam traz `author.steamid`. Podemos ler playtime_at_review
          em memória, mas o dict de saída NUNCA inclui steamid/author.
        - Sem recommendationid → descarta (não dá para deduplicar com segurança).
        """
        recommendationid = raw.get("recommendationid")
        if not recommendationid:
            return None

        # NÃO fazer: return {..., "author": raw["author"]}
        # NÃO fazer: raw.get("author", {}).get("steamid")
        return {
            "recommendationid": str(recommendationid),
            "texto": raw.get("review") or "",
            "recomendada": bool(raw.get("voted_up")),
            "votos_uteis": int(raw.get("votes_up") or 0),
            # Metadado da review (horas jogadas na época), sem identificar a pessoa
            "playtime_at_review": int(
                (raw.get("author") or {}).get("playtime_at_review") or 0
            ),
            "tipo_amostra": tipo_amostra,
        }
