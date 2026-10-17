"""Registro de experimentos em /experiments (JSON por execução).

Cada execução de cluster/treino/avaliação grava parâmetros e métricas, para o TCC
conseguir citar exatamente qual configuração gerou qual número.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ML_ROOT = Path(__file__).resolve().parents[1]


def experiments_dir() -> Path:
    path = Path(os.getenv("EXPERIMENTS_DIR", ML_ROOT.parent / "experiments"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_experiment(name: str, payload: Dict[str, Any]) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = experiments_dir() / f"{name}_{stamp}.json"
    record = {"experimento": name, "executado_em_utc": stamp, **payload}
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
