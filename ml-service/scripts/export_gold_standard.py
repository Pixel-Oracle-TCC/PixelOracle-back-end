"""
Exporta uma amostra de reviews para anotação manual (gold standard da ABSA).

Gera duas planilhas idênticas (anotador1.csv, anotador2.csv) SEM a resposta da Gemini,
para os anotadores não serem influenciados. A amostra é estratificada por
recomendada × idioma e só usa reviews já processadas pela ABSA (para comparar depois).

Formato da coluna "anotacao": gameplay:positivo; historia:negativo   (ou "nenhum")
Categorias válidas: ver absa/taxonomy.py.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from absa.taxonomy import CATEGORIES  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from ml.experiments import experiments_dir  # noqa: E402
from models.orm import Game, Review  # noqa: E402

FIELDS = ["review_id", "jogo", "idioma", "recomendada", "texto", "anotacao"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta amostra para gold standard")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    try:
        rows = (
            session.query(Review.id, Review.texto, Review.language, Review.recomendada, Game.titulo)
            .join(Game, Game.id == Review.game_id)
            .filter(Review.absa_processed_at.isnot(None), Review.absa_model != "curta-demais")
            .all()
        )
    finally:
        session.close()
    if not rows:
        raise SystemExit("Nenhuma review processada pela ABSA. Rode scripts/run_absa.py antes.")

    strata = defaultdict(list)
    for row in rows:
        strata[(bool(row.recomendada), row.language)].append(row)
    rng = random.Random(args.seed)
    sample = []
    for key in sorted(strata, key=str):
        bucket = strata[key]
        rng.shuffle(bucket)
        quota = max(1, round(args.size * len(bucket) / len(rows)))
        sample.extend(bucket[:quota])
    sample = sample[: args.size]

    out_dir = experiments_dir() / "gold_standard"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("anotador1.csv", "anotador2.csv"):
        with (out_dir / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for row in sample:
                writer.writerow(
                    {
                        "review_id": row.id,
                        "jogo": row.titulo,
                        "idioma": row.language,
                        "recomendada": "sim" if row.recomendada else "nao",
                        "texto": row.texto,
                        "anotacao": "",
                    }
                )
    print(f"✅ {len(sample)} reviews exportadas para {out_dir}")
    print("   Preencha a coluna 'anotacao' de forma independente em cada planilha.")
    print(f"   Categorias: {', '.join(CATEGORIES)}")
    print("   Sentimentos: positivo, negativo, neutro | Sem aspecto: nenhum")


if __name__ == "__main__":
    main()
