"""Leitura da planilha, normalização de rótulos, EDA e split por jogo."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from config import (
    ANNOTATOR_COL,
    AXES,
    CLAUDE_MARK,
    CLASSES_7,
    DEFAULT_CSV,
    DEFAULT_SHEET,
    DEFAULT_XLSX,
    GAME_ID_COL,
    LABEL_ALIASES,
    MIN_LABELED_WARN,
    OUTPUTS_DIR,
    RARE_CLASS_WARN,
    REQUIRED_COLUMNS,
    SPLIT_RATIOS,
    SPLIT_SEARCH_SEEDS,
    TEXT_COL,
    VAL_FROM_TRAIN,
)

logger = logging.getLogger(__name__)

_DASHES = ("−", "–", "—", "‑")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_HTML = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_ZW = re.compile(r"[\u200b-\u200d\ufeff]")
_WS = re.compile(r"\s+")


def clean_review_text(raw: Any) -> str:
    """Nulos → vazio; tira controle, HTML, URL e espaços repetidos. Mantém pontuação do português."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return ""
    text = unicodedata.normalize("NFC", str(raw))
    text = _ZW.sub("", text)
    text = _CTRL.sub(" ", text)
    text = _HTML.sub(" ", text)
    text = _URL.sub(" ", text)
    text = text.replace("\xa0", " ")
    return _WS.sub(" ", text).strip()


class InvalidLabelError(ValueError):
    """Rótulo fora do dicionário — não adivinhar."""


class MissingDataError(FileNotFoundError):
    """Arquivo ou coluna obrigatória ausente."""


@dataclass
class FilterStats:
    total_rows: int
    unlabeled_dropped: int
    partial_dropped: int
    short_dropped: int
    invalid_dropped: int
    labeled_kept: int
    n_games: int
    annotator_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class SplitSets:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    game_ids: Dict[str, List[Any]]
    seed_used: int
    distribution_score: float


def _clean_column_name(name: Any) -> str:
    text = str(name).replace("\ufeff", "").strip()
    return text


def normalize_label_token(raw: Any) -> Optional[str]:
    """Devolve código canônico (POS, …) ou None se vazio. Levanta InvalidLabelError se desconhecido."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    if isinstance(raw, (int, np.integer)):
        raw = str(raw)
    text = str(raw).replace("\ufeff", "").strip()
    if text == "" or text.lower() in {"nan", "none", "<na>"}:
        return None
    folded = text.casefold()
    for dash in _DASHES:
        folded = folded.replace(dash, "-")
    folded = re.sub(r"\s+", " ", folded)
    folded = re.sub(r"\(\s+", "(", folded)
    folded = re.sub(r"\s+\)", ")", folded)
    compact = folded.replace(" ", "")
    mapped = LABEL_ALIASES.get(compact)
    if mapped is None:
        raise InvalidLabelError(text)
    return mapped


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_input_path(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise MissingDataError(f"Arquivo de entrada não encontrado: {path}")
        return path
    if DEFAULT_XLSX.is_file():
        return DEFAULT_XLSX
    if DEFAULT_CSV.is_file():
        return DEFAULT_CSV
    raise MissingDataError(
        "Coloque reviews_anotadas.xlsx (aba Reviews) ou reviews_anotadas.csv "
        f"em {DEFAULT_XLSX.parent}"
    )


def load_raw_table(path: Path, sheet: str = DEFAULT_SHEET) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        try:
            frame = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
        except ValueError as exc:
            raise MissingDataError(f"Aba '{sheet}' não existe em {path.name}: {exc}") from exc
    elif suffix == ".csv":
        frame = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    else:
        raise MissingDataError(f"Extensão não suportada: {suffix} (use .xlsx ou .csv)")
    frame.columns = [_clean_column_name(c) for c in frame.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise MissingDataError(f"Colunas obrigatórias ausentes: {missing}. Encontradas: {list(frame.columns)}")
    return frame


def _is_claude(value: Any) -> bool:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False
    return CLAUDE_MARK in str(value).casefold()


def prepare_labeled(
    raw: pd.DataFrame,
    *,
    min_words: int = 0,
    only_human: bool = False,
    drop_invalid: bool = False,
) -> Tuple[pd.DataFrame, FilterStats, List[Dict[str, Any]]]:
    """Remove linhas sem rótulo completo. Rótulo fora do mapa: CSV e, por padrão, aborta."""
    work = raw.copy()
    invalid: List[Dict[str, Any]] = []
    for axis in AXES:
        codes: List[Optional[str]] = []
        for idx, value in work[axis].items():
            try:
                codes.append(normalize_label_token(value))
            except InvalidLabelError as exc:
                invalid.append(
                    {
                        "index": int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                        "eixo": axis,
                        "valor": str(exc),
                    }
                )
                codes.append(None)
        work[axis] = codes

    if invalid:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUTS_DIR / "rotulos_invalidos.csv"
        pd.DataFrame(invalid).to_csv(out, index=False, sep=";", encoding="utf-8-sig")
        if not drop_invalid:
            raise InvalidLabelError(f"{len(invalid)} rótulos inválidos. Lista em {out}")
        logger.warning("Descartando %s linha(s) com rótulo inválido (%s)", len(invalid), out)

    empty_mask = work[list(AXES)].isna().all(axis=1)
    partial_mask = work[list(AXES)].isna().any(axis=1) & ~empty_mask
    unlabeled = int(empty_mask.sum())
    partial = int(partial_mask.sum())
    labeled = work.loc[~empty_mask & ~partial_mask].copy()

    if ANNOTATOR_COL in labeled.columns and only_human:
        labeled = labeled.loc[~labeled[ANNOTATOR_COL].map(_is_claude)].copy()

    labeled[TEXT_COL] = labeled[TEXT_COL].map(clean_review_text)
    empty_text = labeled[TEXT_COL].eq("")
    empty_n = int(empty_text.sum())
    if empty_n:
        logger.info("Descartando %s review(s) com texto nulo/vazio após limpeza", empty_n)
        labeled = labeled.loc[~empty_text].copy()

    word_counts = labeled[TEXT_COL].map(lambda t: len(t.split()))
    labeled = labeled.assign(_n_words=word_counts)
    short = empty_n
    if min_words > 0:
        keep = labeled["_n_words"] >= min_words
        short += int((~keep).sum())
        labeled = labeled.loc[keep].copy()

    labeled[GAME_ID_COL] = labeled[GAME_ID_COL]

    annotator_counts: Dict[str, int] = {}
    if ANNOTATOR_COL in labeled.columns:
        annotator_counts = {
            str(k): int(v)
            for k, v in labeled[ANNOTATOR_COL].fillna("(vazio)").astype(str).value_counts().items()
        }

    stats = FilterStats(
        total_rows=len(work),
        unlabeled_dropped=unlabeled,
        partial_dropped=partial,
        short_dropped=short,
        invalid_dropped=len(invalid),
        labeled_kept=len(labeled),
        n_games=int(labeled[GAME_ID_COL].nunique()) if len(labeled) else 0,
        annotator_counts=annotator_counts,
    )
    logger.info(
        "Filtro: total=%s sem_rótulo=%s parcial=%s inválidos=%s curtas=%s rotuladas=%s jogos=%s",
        stats.total_rows,
        stats.unlabeled_dropped,
        stats.partial_dropped,
        stats.invalid_dropped,
        stats.short_dropped,
        stats.labeled_kept,
        stats.n_games,
    )
    return labeled.reset_index(drop=True), stats, invalid


def word_stats(texts: Iterable[str]) -> Dict[str, Any]:
    counts = np.array([len(str(t).split()) for t in texts], dtype=float)
    if counts.size == 0:
        return {
            "media": 0.0,
            "mediana": 0.0,
            "p90": 0.0,
            "p99": 0.0,
            "lt_20": 0,
            "gt_200": 0,
        }
    return {
        "media": float(np.mean(counts)),
        "mediana": float(np.median(counts)),
        "p90": float(np.percentile(counts, 90)),
        "p99": float(np.percentile(counts, 99)),
        "lt_20": int((counts < 20).sum()),
        "gt_200": int((counts > 200).sum()),
    }


def class_distribution(frame: pd.DataFrame, axis: str) -> pd.DataFrame:
    counts = frame[axis].value_counts()
    rows = []
    n = max(len(frame), 1)
    for cls in CLASSES_7:
        c = int(counts.get(cls, 0))
        rows.append({"classe": cls, "n": c, "pct": 100.0 * c / n})
    return pd.DataFrame(rows)


def _axis_prop_vector(frame: pd.DataFrame) -> np.ndarray:
    vec: List[float] = []
    n = max(len(frame), 1)
    for axis in AXES:
        counts = frame[axis].value_counts()
        for cls in CLASSES_7:
            vec.append(float(counts.get(cls, 0)) / n)
    return np.asarray(vec, dtype=float)


def _assign_games(
    game_sizes: Mapping[Any, int],
    rng: np.random.Generator,
    ratios: Tuple[float, float, float] = SPLIT_RATIOS,
) -> Dict[str, List[Any]]:
    games = list(game_sizes.keys())
    rng.shuffle(games)
    total = float(sum(game_sizes.values()))
    names = ("train", "val", "test")
    active = [name for name, ratio in zip(names, ratios) if ratio > 1e-9]
    targets = {name: ratio * total for name, ratio in zip(names, ratios) if name in active}
    buckets: Dict[str, List[Any]] = {name: [] for name in names}
    filled = {name: 0.0 for name in names}
    for game in games:
        size = float(game_sizes[game])
        choice = max(active, key=lambda name: targets[name] - filled[name])
        buckets[choice].append(game)
        filled[choice] += size
    return buckets


def split_by_game(
    labeled: pd.DataFrame,
    *,
    search_seeds: Sequence[int] = SPLIT_SEARCH_SEEDS,
    test_human_only: bool = False,
) -> SplitSets:
    """Split agrupado por game_id (padrão 80/20 treino/teste). Busca semente com menor desvio."""
    if labeled.empty:
        raise ValueError("Não há reviews rotuladas para dividir.")
    sizes = labeled.groupby(GAME_ID_COL).size().to_dict()
    overall = _axis_prop_vector(labeled)
    best: Optional[SplitSets] = None

    for seed in search_seeds:
        rng = np.random.default_rng(seed)
        buckets = _assign_games(sizes, rng)
        parts = {
            name: labeled.loc[labeled[GAME_ID_COL].isin(ids)].copy()
            for name, ids in buckets.items()
        }
        if test_human_only and ANNOTATOR_COL in labeled.columns:
            human = ~parts["test"][ANNOTATOR_COL].map(_is_claude)
            parts["test"] = parts["test"].loc[human].copy()
            if parts["test"].empty:
                continue
        used = [name for name in ("train", "val", "test") if len(parts[name]) > 0]
        score = float(sum(np.abs(_axis_prop_vector(parts[name]) - overall).sum() for name in used))
        candidate = SplitSets(
            train=parts["train"],
            val=parts["val"],
            test=parts["test"],
            game_ids={k: [x for x in v] for k, v in buckets.items()},
            seed_used=int(seed),
            distribution_score=score,
        )
        if best is None or candidate.distribution_score < best.distribution_score:
            best = candidate
    assert best is not None
    _assert_no_leakage(best)
    logger.info(
        "Split seed=%s score=%.4f sizes train/val/test=%s/%s/%s",
        best.seed_used,
        best.distribution_score,
        len(best.train),
        len(best.val),
        len(best.test),
    )
    return best


def carve_val_from_train(split: SplitSets, frac: float = VAL_FROM_TRAIN, seed: int = 0) -> SplitSets:
    """Separa uma fatia do treino para validação (o teste de 20% não é tocado)."""
    if frac <= 0 or split.train.empty:
        return split
    sizes = split.train.groupby(GAME_ID_COL).size().to_dict()
    games = list(sizes.keys())
    rng = np.random.default_rng(seed)
    rng.shuffle(games)
    target = frac * float(len(split.train))
    val_games: List[Any] = []
    acc = 0.0
    for game in games:
        if acc >= target and val_games:
            break
        val_games.append(game)
        acc += float(sizes[game])
    val_set = set(val_games)
    train_games = [g for g in games if g not in val_set]
    if not train_games or not val_games:
        return split
    train = split.train.loc[split.train[GAME_ID_COL].isin(train_games)].copy()
    val = split.train.loc[split.train[GAME_ID_COL].isin(val_games)].copy()
    carved = SplitSets(
        train=train,
        val=val,
        test=split.test.copy(),
        game_ids={
            "train": train_games,
            "val": val_games,
            "test": list(split.game_ids["test"]),
        },
        seed_used=split.seed_used,
        distribution_score=split.distribution_score,
    )
    _assert_no_leakage(carved)
    logger.info(
        "Val recortado do treino: train %s / val %s / test %s",
        len(carved.train),
        len(carved.val),
        len(carved.test),
    )
    return carved


def _assert_no_leakage(split: SplitSets) -> None:
    sets = {name: set(map(str, ids)) for name, ids in split.game_ids.items()}
    if sets["train"] & sets["val"] or sets["train"] & sets["test"] or sets["val"] & sets["test"]:
        raise RuntimeError("Vazamento: o mesmo game_id aparece em mais de um conjunto.")
    texts = {
        "train": set(split.train[TEXT_COL].astype(str)),
        "val": set(split.val[TEXT_COL].astype(str)) if len(split.val) else set(),
        "test": set(split.test[TEXT_COL].astype(str)),
    }
    if texts["train"] & texts["val"] or texts["train"] & texts["test"] or texts["val"] & texts["test"]:
        raise RuntimeError("Vazamento: o mesmo texto aparece em conjuntos diferentes.")


def save_split(split: SplitSets, path: Optional[Path] = None) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = path or (OUTPUTS_DIR / "split.json")
    payload = {
        "seed_used": split.seed_used,
        "distribution_score": split.distribution_score,
        "n_reviews": {
            "train": int(len(split.train)),
            "val": int(len(split.val)),
            "test": int(len(split.test)),
        },
        "game_ids": {k: [str(x) for x in v] for k, v in split.game_ids.items()},
    }
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def load_split(labeled: pd.DataFrame, path: Path) -> SplitSets:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = payload["game_ids"]
    parts = {
        name: labeled.loc[labeled[GAME_ID_COL].astype(str).isin(ids[name])].copy()
        for name in ("train", "val", "test")
    }
    split = SplitSets(
        train=parts["train"],
        val=parts["val"],
        test=parts["test"],
        game_ids=ids,
        seed_used=int(payload["seed_used"]),
        distribution_score=float(payload["distribution_score"]),
    )
    _assert_no_leakage(split)
    return split


def all_nm_mask(frame: pd.DataFrame) -> pd.Series:
    return frame[list(AXES)].eq("NM").all(axis=1)


def write_eda_md(
    labeled: pd.DataFrame,
    stats: FilterStats,
    *,
    data_path: Path,
    data_hash: str,
    split: Optional[SplitSets] = None,
    dest: Optional[Path] = None,
) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = dest or (OUTPUTS_DIR / "eda.md")
    wstats = word_stats(labeled[TEXT_COL].tolist()) if len(labeled) else word_stats([])
    rare: List[str] = []
    missing_class: List[str] = []
    lines: List[str] = [
        "# EDA — reviews anotadas (Tétrade de Schell)",
        "",
        f"- Arquivo: `{data_path.name}`",
        f"- SHA-256: `{data_hash}`",
        f"- Linhas no arquivo: **{stats.total_rows}**",
        f"- Sem nenhum eixo preenchido (removidas): **{stats.unlabeled_dropped}**",
        f"- Parcialmente preenchidas (removidas): **{stats.partial_dropped}**",
        f"- Rótulo inválido (não mapeado): **{stats.invalid_dropped}**",
        f"- Removidas por MIN_WORDS: **{stats.short_dropped}**",
        f"- Rotuladas usadas: **{stats.labeled_kept}**",
        f"- Jogos distintos (rotuladas): **{stats.n_games}**",
        "",
    ]
    if stats.labeled_kept < MIN_LABELED_WARN:
        lines += [
            f"> **Aviso:** menos de {MIN_LABELED_WARN} linhas rotuladas "
            f"({stats.labeled_kept}). Métricas instáveis — use `--smoke` até haver mais anotações.",
            "",
        ]
    if stats.annotator_counts:
        lines += ["## Anotador", ""]
        for name, n in stats.annotator_counts.items():
            lines.append(f"- `{name}`: {n}")
        lines.append("")

    lines += ["## Distribuição das 7 classes por eixo", ""]
    for axis in AXES:
        dist = class_distribution(labeled, axis)
        lines.append(f"### {axis}")
        lines.append("")
        lines.append("| Classe | n | % |")
        lines.append("|---|---:|---:|")
        for _, row in dist.iterrows():
            lines.append(f"| {row['classe']} | {int(row['n'])} | {row['pct']:.1f} |")
            if int(row["n"]) == 0:
                missing_class.append(f"{axis}/{row['classe']}")
            elif int(row["n"]) < RARE_CLASS_WARN:
                rare.append(f"{axis}/{row['classe']} ({int(row['n'])})")
        lines.append("")

    if rare:
        lines += ["**Classes com menos de 30 exemplos:** " + ", ".join(rare), ""]
    if missing_class:
        lines += ["**Classes ausentes:** " + ", ".join(missing_class), ""]

    nm = int(all_nm_mask(labeled).sum()) if len(labeled) else 0
    nm_pct = 100.0 * nm / stats.labeled_kept if stats.labeled_kept else 0.0
    lines += [
        "## Tamanho do texto (palavras)",
        "",
        f"- média {wstats['media']:.1f}, mediana {wstats['mediana']:.1f}, "
        f"p90 {wstats['p90']:.1f}, p99 {wstats['p99']:.1f}",
        f"- < 20 palavras: {wstats['lt_20']}",
        f"- > 200 palavras: {wstats['gt_200']}",
        "",
        "## Quatro eixos = Não mencionado",
        "",
        f"- {nm} reviews ({nm_pct:.1f}%)",
        "",
    ]
    if split is not None:
        lines += [
            "## Split por jogo",
            "",
            f"- semente escolhida: {split.seed_used} (menor desvio de distribuição)",
            f"- train {len(split.train)} / val {len(split.val)} / test {len(split.test)} reviews",
            f"- jogos train/val/test: {len(split.game_ids['train'])} / "
            f"{len(split.game_ids['val'])} / {len(split.game_ids['test'])}",
            "",
        ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest
