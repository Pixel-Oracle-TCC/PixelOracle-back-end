"""Tabelas markdown/CSV, predições e registro de versões."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pandas as pd

from config import ANNOTATOR_COL, AXES, GAME_ID_COL, OUTPUTS_DIR, TEXT_COL


def _md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_sem linhas_"
    cols = [str(c) for c in frame.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, row in frame.iterrows():
        cells = []
        for c in frame.columns:
            val = row[c]
            if isinstance(val, float):
                cells.append(f"{val:.4f}")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body])


def library_versions() -> Dict[str, str]:
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for name in ("pandas", "numpy", "sklearn", "torch", "transformers", "matplotlib"):
        try:
            mod = __import__(name if name != "sklearn" else "sklearn")
            versions[name] = getattr(mod, "__version__", "desconhecida")
        except Exception:  # noqa: BLE001
            versions[name] = "não instalada"
    return versions


def write_predictions(
    test: pd.DataFrame,
    preds: Mapping[str, Sequence[str]],
    *,
    model: str,
    scheme: str,
    seed: int,
) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    n = len(test)
    annot = test[ANNOTATOR_COL].tolist() if ANNOTATOR_COL in test.columns else [""] * n
    games = test[GAME_ID_COL].tolist()
    texts = test[TEXT_COL].tolist()
    for i in range(n):
        row: Dict[str, Any] = {
            "game_id": games[i],
            "texto": texts[i],
            "anotador": annot[i],
            "modelo": model,
            "esquema": scheme,
            "semente": seed,
        }
        for axis in AXES:
            row[f"{axis}_gold"] = test.iloc[i][axis]
            key = axis if axis in preds else None
            if key:
                row[f"{axis}_pred"] = preds[axis][i]
            else:
                for marker in ("mencionado", "elogio", "critica"):
                    mk = f"{axis}:{marker}"
                    if mk in preds:
                        row[f"{axis}_{marker}_pred"] = preds[mk][i]
        rows.append(row)
    dest = OUTPUTS_DIR / f"predicoes_{model}_{scheme}.csv"
    mode = "a" if dest.exists() else "w"
    header = not dest.exists()
    pd.DataFrame(rows).to_csv(dest, sep=";", index=False, encoding="utf-8-sig", mode=mode, header=header)
    return dest


def append_result_row(
    rows: List[Dict[str, Any]],
    *,
    model: str,
    scheme: str,
    seed: int,
    summary: Mapping[str, Mapping[str, float]],
) -> None:
    row: Dict[str, Any] = {"modelo": model, "esquema": scheme, "semente": seed}
    for axis in AXES:
        row[f"{axis}_macro_f1"] = summary.get(axis, {}).get("macro_f1")
        row[f"{axis}_acc"] = summary.get(axis, {}).get("accuracy")
    row["media_macro_f1"] = summary.get("_mean", {}).get("macro_f1")
    rows.append(row)


def write_results_table(
    rows: List[Dict[str, Any]],
    *,
    versions: Mapping[str, str],
    data_hash: str,
    notes: Sequence[str],
) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    csv_path = OUTPUTS_DIR / "resultados.csv"
    frame.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")

    md: List[str] = [
        "# Resultados — sentimento por eixo",
        "",
        f"- gerado em UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- hash dos dados: `{data_hash}`",
        f"- versões: {json.dumps(dict(versions), ensure_ascii=False)}",
        "",
        "## Tabela por execução",
        "",
        _md_table(frame),
        "",
    ]
    if not frame.empty and "media_macro_f1" in frame.columns:
        agg = (
            frame.groupby(["modelo", "esquema"], as_index=False)["media_macro_f1"]
            .agg(["mean", "std"])
            .reset_index()
        )
        md += ["## Agregado (média ± desvio das sementes)", "", _md_table(agg), ""]
    if notes:
        md += ["## Notas", ""] + [f"- {n}" for n in notes] + [""]
    dest = OUTPUTS_DIR / "resultados.md"
    dest.write_text("\n".join(md), encoding="utf-8")
    return dest
