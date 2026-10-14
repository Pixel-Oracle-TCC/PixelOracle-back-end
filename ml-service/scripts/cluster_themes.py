"""
Script offline: transforma aspectos extraídos em temas recorrentes.

1) Gera embedding do "resumo" de cada aspecto ainda sem vetor (modelo multilíngue).
2) Recria os temas do zero: dentro de cada (categoria, polaridade), agrupa os resumos.
3) A Gemini só nomeia cada cluster a partir de resumos reais (fallback: representante).
4) Registra silhouette e cobertura em /experiments.

Aspectos neutros não viram tema (não são elogio nem reclamação).
Rodar de novo recria os temas e apaga theme_stats (cascade) — rode
compute_theme_stats.py e ml/train_drivers.py em seguida.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML_ROOT))
load_dotenv(ML_ROOT / ".env")

from absa.taxonomy import POLARITIES  # noqa: E402
from db.connection import init_engine, session_scope  # noqa: E402
from embeddings.encoder import get_aspect_encoder  # noqa: E402
from ml.experiments import log_experiment  # noqa: E402
from models.orm import ReviewAspect, Theme  # noqa: E402
from themes.clustering import NOISE, cluster_embeddings, representatives  # noqa: E402
from themes.naming import name_clusters  # noqa: E402


def embed_missing(session, batch_size: int) -> int:
    encoder = get_aspect_encoder()
    pending = (
        session.query(ReviewAspect)
        .filter(ReviewAspect.embedding.is_(None), ReviewAspect.resumo.isnot(None))
        .order_by(ReviewAspect.id)
        .all()
    )
    for start in range(0, len(pending), batch_size):
        chunk = pending[start : start + batch_size]
        vectors = encoder.encode_batch([a.resumo for a in chunk])
        for aspect, vector in zip(chunk, vectors):
            aspect.embedding = vector
        session.commit()
    return len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster de temas recorrentes")
    parser.add_argument("--distance-threshold", type=float, default=0.35)
    parser.add_argument("--min-cluster-size", type=int, default=5)
    parser.add_argument("--embed-batch", type=int, default=256)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if init_engine() is None:
        raise SystemExit("DATABASE_URL não configurada.")

    session = session_scope()
    try:
        embedded = embed_missing(session, args.embed_batch)
        print(f"🔢 Embeddings novos de resumos: {embedded}")

        session.query(ReviewAspect).update({ReviewAspect.theme_id: None})
        session.query(Theme).delete()
        session.commit()

        aspects = (
            session.query(ReviewAspect.id, ReviewAspect.categoria, ReviewAspect.sentimento,
                          ReviewAspect.resumo, ReviewAspect.embedding)
            .filter(ReviewAspect.embedding.isnot(None), ReviewAspect.sentimento.in_(POLARITIES))
            .all()
        )
        groups: dict[tuple[str, str], list] = defaultdict(list)
        for row in aspects:
            groups[(row.categoria, row.sentimento)].append(row)

        pending_names: dict[str, dict] = {}
        theme_members: dict[str, list[int]] = {}
        theme_meta: dict[str, dict] = {}
        metrics = []

        for (categoria, polaridade), rows in sorted(groups.items()):
            vectors = np.array([np.asarray(r.embedding, dtype=np.float32) for r in rows])
            result = cluster_embeddings(
                vectors,
                distance_threshold=args.distance_threshold,
                min_cluster_size=args.min_cluster_size,
            )
            clustered = int((result.labels != NOISE).sum())
            metrics.append(
                {
                    "categoria": categoria,
                    "polaridade": polaridade,
                    "aspectos": len(rows),
                    "temas": len(result.centroids),
                    "cobertura": round(clustered / len(rows), 4) if rows else 0.0,
                    "silhouette": result.silhouette,
                }
            )
            for label, centroid in result.centroids.items():
                gid = f"{categoria}-{polaridade}-{label}"
                rep_idx = representatives(vectors, result.labels, centroid, label)
                pending_names[gid] = {
                    "categoria": categoria,
                    "polaridade": polaridade,
                    "amostras": [rows[i].resumo for i in rep_idx],
                }
                theme_members[gid] = [rows[i].id for i in np.where(result.labels == label)[0]]
                theme_meta[gid] = {"centroide": centroid.tolist()}

        names = name_clusters(pending_names)
        for gid, data in pending_names.items():
            rotulo, fonte = names[gid]
            theme = Theme(
                categoria=data["categoria"],
                polaridade=data["polaridade"],
                rotulo=rotulo,
                tamanho=len(theme_members[gid]),
                centroide=theme_meta[gid]["centroide"],
                rotulo_fonte=fonte,
            )
            session.add(theme)
            session.flush()
            session.query(ReviewAspect).filter(ReviewAspect.id.in_(theme_members[gid])).update(
                {ReviewAspect.theme_id: theme.id}, synchronize_session=False
            )
        session.commit()

        total = len(aspects)
        covered = sum(len(v) for v in theme_members.values())
        path = log_experiment(
            "temas",
            {
                "parametros": {
                    "distance_threshold": args.distance_threshold,
                    "min_cluster_size": args.min_cluster_size,
                    "modelo_embedding": get_aspect_encoder().model_name,
                },
                "aspectos_polarizados": total,
                "temas": len(pending_names),
                "cobertura_global": round(covered / total, 4) if total else 0.0,
                "por_grupo": metrics,
            },
        )
        print(f"✅ Temas criados: {len(pending_names)} | cobertura {covered}/{total} | log: {path}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
