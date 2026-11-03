"""Caminhos da POC da Tétrade. Não abre a Gemini e não chama a Steam."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API_ROOT / "ml-service"))
sys.path.insert(0, str(API_ROOT / "poc"))

from _lib.bootstrap import open_session, write_json  # noqa: E402

TETRADE_ROOT = API_ROOT / "poc" / "tetrade"
DADOS = TETRADE_ROOT / "dados"
AMOSTRA_IDS = DADOS / "amostra_ids.csv"
DIVISAO = DADOS / "divisao.json"
ROTULOS = DADOS / "rotulos.csv"
PREDICOES = TETRADE_ROOT / "04-piso-sem-rede" / "output" / "predicoes_validacao.csv"


def ler_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ler_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def gravar_csv(path: Path, rows: list[dict], campos: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
