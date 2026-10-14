"""
Script offline: extrai aspectos (ABSA multi-aspecto) das reviews ainda não processadas.

Idempotente: só pega reviews com absa_processed_at NULL. Ao reprocessar (--reprocess),
apaga os aspectos antigos da review antes de gravar os novos.
Registra o modelo Gemini usado em reviews.absa_model (rastreabilidade para o TCC).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from absa.extractor import AbsaExtractor  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from models.orm import Review, ReviewAspect  # noqa: E402

MIN_TEXT_CHARS = 20


def main() -> None:
    parser = argparse.ArgumentParser(description="ABSA multi-aspecto via Gemini")
    parser.add_argument("--limit", type=int, default=500, help="Máximo de reviews nesta execução")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--reprocess", action="store_true", help="Refaz reviews já processadas")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    extractor = AbsaExtractor()
    if not extractor.client.available:
        raise SystemExit("GEMINI_API_KEY não configurada em ml-service/.env.")

    session = session_scope()
    try:
        query = session.query(Review).order_by(Review.id)
        if not args.reprocess:
            query = query.filter(Review.absa_processed_at.is_(None))
        reviews = query.limit(args.limit).all()

        # Textos muito curtos ("good", "10/10") não têm aspecto: marca como processado vazio
        too_short = [r for r in reviews if len((r.texto or "").strip()) < MIN_TEXT_CHARS]
        to_extract = [r for r in reviews if r not in too_short]
        print(f"🧠 Reviews: {len(reviews)} | para Gemini: {len(to_extract)} | curtas: {len(too_short)}")

        now = datetime.utcnow()
        for review in too_short:
            review.absa_processed_at = now
            review.absa_model = "curta-demais"
        session.commit()

        total_aspects = 0
        step = args.batch_size * 5
        for start in range(0, len(to_extract), step):
            block = to_extract[start : start + step]
            payload = [{"recommendationid": r.recommendationid, "texto": r.texto} for r in block]
            results = extractor.extract_batch(payload, batch_size=args.batch_size)
            for review in block:
                aspects = results.get(str(review.recommendationid))
                if aspects is None:
                    continue  # lote falhou → fica pendente para a próxima execução
                session.query(ReviewAspect).filter(ReviewAspect.review_id == review.id).delete()
                for aspect in aspects:
                    session.add(ReviewAspect(review_id=review.id, **aspect))
                review.absa_processed_at = datetime.utcnow()
                review.absa_model = extractor.model_name
                total_aspects += len(aspects)
            session.commit()
            print(
                f"... {min(start + step, len(to_extract))}/{len(to_extract)} | aspectos: {total_aspects}",
                flush=True,
            )
            if extractor.quota_exhausted:
                print("⛔ Cota diária da Gemini esgotada: parcial gravado, o resto fica pendente.")
                break

        print(f"✅ ABSA concluída. Aspectos gravados: {total_aspects}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
