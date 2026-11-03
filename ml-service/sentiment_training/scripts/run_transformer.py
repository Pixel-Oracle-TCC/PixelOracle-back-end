#!/usr/bin/env python3
"""Treina BERTimbau ou XLM-R multi-cabeça."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import DEFAULT_SHEET, MIN_LABELED_WARN, OUTPUTS_DIR, SEEDS, TRANSFORMER_MODELS  # noqa: E402
from data import (  # noqa: E402
    InvalidLabelError,
    MissingDataError,
    carve_val_from_train,
    file_sha256,
    load_raw_table,
    load_split,
    prepare_labeled,
    resolve_input_path,
    save_split,
    split_by_game,
)
from report import append_result_row, library_versions, write_predictions, write_results_table  # noqa: E402
from transformer import evaluate_transformer, predict_transformer, train_transformer  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(TRANSFORMER_MODELS), required=True)
    parser.add_argument("--scheme", choices=("7", "5", "binary"), default="7")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--min-words", type=int, default=0)
    parser.add_argument("--only-human", action="store_true")
    parser.add_argument("--test-human-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--drop-invalid", action="store_true")
    parser.add_argument("--allow-small", action="store_true")
    parser.add_argument("--force-split", action="store_true")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    args = parser.parse_args()

    try:
        path = resolve_input_path(args.input)
        raw = load_raw_table(path, args.sheet)
        labeled, stats, _ = prepare_labeled(
            raw,
            min_words=args.min_words,
            only_human=args.only_human,
            drop_invalid=args.drop_invalid,
        )
    except (MissingDataError, InvalidLabelError) as exc:
        logging.error("%s", exc)
        return 2

    if stats.labeled_kept < MIN_LABELED_WARN and not args.smoke and not args.allow_small:
        logging.error(
            "Só %s linhas rotuladas (< %s). Rode com --smoke ou --allow-small.",
            stats.labeled_kept,
            MIN_LABELED_WARN,
        )
        return 3

    split_path = OUTPUTS_DIR / "split.json"
    if split_path.is_file() and not args.force_split:
        split = load_split(labeled, split_path)
    else:
        split = split_by_game(labeled, test_human_only=args.test_human_only)
        save_split(split)

    if split.val.empty:
        split = carve_val_from_train(split)
    train, val, test = split.train, split.val, split.test
    if args.smoke:
        train, val, test = train.head(8), val.head(4), test.head(4)
        args.seeds = args.seeds[:1]

    hf_name = TRANSFORMER_MODELS[args.model]
    rows = []
    notes = []
    digest = file_sha256(path)
    for seed in args.seeds:
        logging.info("%s seed=%s scheme=%s ckpt=%s", args.model, seed, args.scheme, hf_name)
        result = train_transformer(
            train,
            val,
            model_key=args.model,
            model_name=hf_name,
            scheme=args.scheme,
            seed=seed,
            smoke=args.smoke,
        )
        summary = evaluate_transformer(
            result,
            test,
            scheme=args.scheme,
            stem_prefix=f"cm_{args.model}_{args.scheme}_{seed}",
        )
        preds = predict_transformer(result, test, scheme=args.scheme)
        write_predictions(test, preds, model=args.model, scheme=args.scheme, seed=seed)
        append_result_row(rows, model=args.model, scheme=args.scheme, seed=seed, summary=summary)
        notes.append(
            f"{args.model} seed {seed} val={result.best_val_f1:.4f} "
            f"test_mean={summary['_mean']['macro_f1']:.4f} ckpt={result.checkpoint}"
        )

    write_results_table(rows, versions=library_versions(), data_hash=digest, notes=notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
