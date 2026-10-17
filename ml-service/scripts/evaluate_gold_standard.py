"""
Avalia a ABSA contra o gold standard anotado manualmente.

1) Kappa entre anotador1.csv e anotador2.csv (confiabilidade da anotação humana).
2) F1 da Gemini contra o consenso:
   - se existir consenso.csv (divergências resolvidas em conjunto), usa ele;
   - senão, usa só as reviews em que os dois anotadores concordaram por completo.
Grava as anotações em absa_gold_standard e as métricas em /experiments.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from absa.validation import multilabel_f1, multilabel_kappa, parse_annotation, to_pairs  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from ml.experiments import experiments_dir, log_experiment  # noqa: E402
from models.orm import AbsaGoldStandard, Review, ReviewAspect  # noqa: E402


def read_sheet(path: Path) -> dict[int, list]:
    with path.open(encoding="utf-8") as handle:
        return {
            int(row["review_id"]): parse_annotation(row.get("anotacao", ""))
            for row in csv.DictReader(handle)
            if (row.get("anotacao") or "").strip()
        }


def main() -> None:
    folder = experiments_dir() / "gold_standard"
    ann1 = read_sheet(folder / "anotador1.csv")
    ann2 = read_sheet(folder / "anotador2.csv")
    consensus_path = folder / "consenso.csv"

    kappa = multilabel_kappa(ann1, ann2)
    print(f"🤝 Kappa entre anotadores: {kappa}")

    if consensus_path.exists():
        gold = read_sheet(consensus_path)
        gold_source = "consenso.csv"
    else:
        gold = {rid: ann1[rid] for rid in set(ann1) & set(ann2) if to_pairs(ann1[rid]) == to_pairs(ann2[rid])}
        gold_source = "concordancia_total_entre_anotadores"

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")
    session = session_scope()
    try:
        ids = sorted(set(ann1) | set(ann2))
        aspects = session.query(ReviewAspect).filter(ReviewAspect.review_id.in_(ids)).all()
        processed = {
            r.id for r in session.query(Review.id).filter(Review.id.in_(ids), Review.absa_processed_at.isnot(None))
        }
        gemini: dict[int, list] = {rid: [] for rid in processed}
        for aspect in aspects:
            gemini.setdefault(aspect.review_id, []).append(
                {"categoria": aspect.categoria, "sentimento": aspect.sentimento}
            )

        f1 = multilabel_f1(gold, gemini)
        print(f"🎯 F1 Gemini vs gold ({gold_source}): {f1}")

        for rid in ids:
            stmt = insert(AbsaGoldStandard).values(
                review_id=rid,
                anotador1=ann1.get(rid),
                anotador2=ann2.get(rid),
                consenso=gold.get(rid),
                gemini=gemini.get(rid),
                updated_at=datetime.utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["review_id"],
                set_={c: getattr(stmt.excluded, c) for c in ("anotador1", "anotador2", "consenso", "gemini", "updated_at")},
            )
            session.execute(stmt)
        session.commit()
    finally:
        session.close()

    path = log_experiment("gold_standard_absa", {"fonte_gold": gold_source, "kappa": kappa, "f1": f1})
    print(f"✅ Avaliação registrada: {path}")


if __name__ == "__main__":
    main()
