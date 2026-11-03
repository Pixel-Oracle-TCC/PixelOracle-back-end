#!/usr/bin/env python3
"""Passo 0: EDA + split por jogo. Não treina modelos."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import DEFAULT_SHEET, MIN_LABELED_WARN, OUTPUTS_DIR  # noqa: E402
from data import (  # noqa: E402
    InvalidLabelError,
    MissingDataError,
    file_sha256,
    load_raw_table,
    prepare_labeled,
    resolve_input_path,
    save_split,
    split_by_game,
    write_eda_md,
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="EDA das reviews anotadas")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--min-words", type=int, default=0)
    parser.add_argument("--only-human", action="store_true")
    parser.add_argument("--test-human-only", action="store_true")
    parser.add_argument(
        "--drop-invalid",
        action="store_true",
        help="Descarta linhas com rótulo fora do dicionário em vez de abortar",
    )
    args = parser.parse_args()

    try:
        path = resolve_input_path(args.input)
        raw = load_raw_table(path, sheet=args.sheet)
        labeled, stats, _ = prepare_labeled(
            raw,
            min_words=args.min_words,
            only_human=args.only_human,
            drop_invalid=args.drop_invalid,
        )
    except (MissingDataError, InvalidLabelError) as exc:
        logging.error("%s", exc)
        return 2

    digest = file_sha256(path)
    split = None
    if stats.labeled_kept > 0:
        split = split_by_game(labeled, test_human_only=args.test_human_only)
        save_split(split)
    dest = write_eda_md(labeled, stats, data_path=path, data_hash=digest, split=split)
    print(dest.read_text(encoding="utf-8"))
    if stats.labeled_kept < MIN_LABELED_WARN:
        logging.warning(
            "Poucas linhas rotuladas (%s). Não inicie o treino completo; use --smoke após confirmar.",
            stats.labeled_kept,
        )
    print(f"\nArquivos: {dest} e {OUTPUTS_DIR / 'split.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
