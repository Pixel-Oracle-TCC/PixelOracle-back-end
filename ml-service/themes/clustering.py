"""Agrupamento de resumos de aspecto em temas recorrentes.

Por quê Agglomerative (cosseno, average linkage) com distance_threshold:
- não exige escolher k (não sabemos quantos temas existem por categoria);
- o limiar de distância tem leitura direta ("resumos com cosseno > 0.65 são o mesmo tema");
- determinístico (KMeans/HDBSCAN variam mais com a amostra).
Custo O(n²) de memória: acima de max_points, ajusta numa amostra e atribui o resto
ao centróide mais próximo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

NOISE = -1


@dataclass
class ClusteringResult:
    labels: np.ndarray            # -1 = ruído / cluster pequeno demais
    centroids: dict               # label -> vetor normalizado
    silhouette: Optional[float]   # None quando há menos de 2 clusters


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _centroids(vectors: np.ndarray, labels: np.ndarray) -> dict:
    result = {}
    for label in sorted(set(labels.tolist())):
        if label == NOISE:
            continue
        mean = vectors[labels == label].mean(axis=0, keepdims=True)
        result[label] = _normalize(mean)[0]
    return result


def cluster_embeddings(
    vectors: np.ndarray,
    *,
    distance_threshold: float = 0.35,
    min_cluster_size: int = 5,
    max_points: int = 6000,
    random_state: int = 42,
) -> ClusteringResult:
    n = len(vectors)
    if n == 0:
        return ClusteringResult(np.array([], dtype=int), {}, None)
    vectors = _normalize(np.asarray(vectors, dtype=np.float32))
    if n < min_cluster_size:
        return ClusteringResult(np.full(n, NOISE), {}, None)

    if n > max_points:
        rng = np.random.default_rng(random_state)
        sample_idx = rng.choice(n, size=max_points, replace=False)
        sample_labels = _fit(vectors[sample_idx], distance_threshold)
        centroids = _centroids(vectors[sample_idx], sample_labels)
        labels = _assign_to_nearest(vectors, centroids, distance_threshold)
    else:
        labels = _fit(vectors, distance_threshold)

    labels = _drop_small(labels, min_cluster_size)
    centroids = _centroids(vectors, labels)
    return ClusteringResult(labels, centroids, _silhouette(vectors, labels, random_state))


def _fit(vectors: np.ndarray, distance_threshold: float) -> np.ndarray:
    if len(vectors) < 2:
        return np.zeros(len(vectors), dtype=int)
    model = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
    )
    return model.fit_predict(vectors)


def _assign_to_nearest(vectors: np.ndarray, centroids: dict, distance_threshold: float) -> np.ndarray:
    if not centroids:
        return np.full(len(vectors), NOISE)
    keys = list(centroids.keys())
    matrix = np.stack([centroids[k] for k in keys])
    similarity = vectors @ matrix.T
    best = similarity.argmax(axis=1)
    best_distance = 1 - similarity[np.arange(len(vectors)), best]
    labels = np.array([keys[i] for i in best])
    labels[best_distance > distance_threshold] = NOISE
    return labels


def _drop_small(labels: np.ndarray, min_cluster_size: int) -> np.ndarray:
    labels = labels.copy()
    values, counts = np.unique(labels, return_counts=True)
    for value, count in zip(values, counts):
        if value != NOISE and count < min_cluster_size:
            labels[labels == value] = NOISE
    return labels


def _silhouette(vectors: np.ndarray, labels: np.ndarray, random_state: int) -> Optional[float]:
    mask = labels != NOISE
    if mask.sum() < 3 or len(set(labels[mask].tolist())) < 2:
        return None
    sample_size = min(2000, int(mask.sum()))
    return float(
        silhouette_score(
            vectors[mask],
            labels[mask],
            metric="cosine",
            sample_size=sample_size,
            random_state=random_state,
        )
    )


def representatives(
    vectors: np.ndarray, labels: np.ndarray, centroid: np.ndarray, label: int, k: int = 8
) -> List[int]:
    """Índices dos k pontos mais próximos do centróide (amostra para nomear o tema)."""
    idx = np.where(labels == label)[0]
    if len(idx) == 0:
        return []
    vecs = _normalize(np.asarray(vectors, dtype=np.float32)[idx])
    order = np.argsort(-(vecs @ centroid))
    return idx[order[:k]].tolist()
