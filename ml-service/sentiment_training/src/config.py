"""Caminhos, hiperparâmetros e mapa de rótulos da Tétrade Elemental."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, FrozenSet, List, Mapping, Sequence, Tuple

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE_ROOT / "data"
OUTPUTS_DIR = PACKAGE_ROOT / "outputs"
CHECKPOINTS_DIR = PACKAGE_ROOT / "checkpoints"

DEFAULT_XLSX = DATA_DIR / "reviews_anotadas.xlsx"
DEFAULT_CSV = DATA_DIR / "reviews_anotadas.csv"
DEFAULT_SHEET = "Reviews"

AXES: Tuple[str, ...] = ("Mecânica", "Narrativa", "Estética", "Tecnologia")
TEXT_COL = "texto"
GAME_ID_COL = "game_id"
ANNOTATOR_COL = "anotador"
CLAUDE_MARK = "claude"

REQUIRED_COLUMNS: FrozenSet[str] = frozenset(
    (GAME_ID_COL, TEXT_COL, *AXES)
)

IGNORE_FOR_TRAINING: FrozenSet[str] = frozenset(
    {
        "anotador",
        "observacao_claude",
        "linha_na_aba_Reviews",
        "jogo_titulo",
        "steam_appid",
    }
)

# 7 classes canônicas
CLASSES_7: Tuple[str, ...] = (
    "POS",
    "NEG",
    "NEU",
    "MAJ_POS",
    "DIV",
    "MAJ_NEG",
    "NM",
)
CLASSES_5: Tuple[str, ...] = ("POS", "NEG", "NEU", "MISTO", "NM")
BINARY_MARKERS: Tuple[str, ...] = ("mencionado", "elogio", "critica")
MIXED_7: FrozenSet[str] = frozenset({"MAJ_POS", "DIV", "MAJ_NEG"})

# chaves já casefold, sem espaços internos, hífen unificado
LABEL_ALIASES: Mapping[str, str] = {
    "positivo": "POS",
    "negativo": "NEG",
    "neutro": "NEU",
    "misto(+)": "MAJ_POS",
    "majoritariamentepositivo": "MAJ_POS",
    "misto(=)": "DIV",
    "dividido": "DIV",
    "misto": "DIV",
    "misto(-)": "MAJ_NEG",
    "majoritariamentenegativo": "MAJ_NEG",
    "nãomencionado": "NM",
    "naomencionado": "NM",
}

ORDINAL_ORDER: Tuple[str, ...] = ("NEG", "MAJ_NEG", "DIV", "MAJ_POS", "POS")
ORDINAL_EXCLUDE: FrozenSet[str] = frozenset({"NM", "NEU"})

SEEDS: Tuple[int, ...] = (13, 42, 2024)
# 80% treino / 20% teste (sem val global). O val do modelo é recortado do treino.
SPLIT_RATIOS: Tuple[float, float, float] = (0.80, 0.0, 0.20)
VAL_FROM_TRAIN = 0.15
SPLIT_SEARCH_SEEDS: Sequence[int] = tuple(range(40))
MIN_LABELED_WARN = 300
RARE_CLASS_WARN = 30

BERTIMBAU = "neuralmind/bert-base-portuguese-cased"
XLMR = "xlm-roberta-base"
TRANSFORMER_MODELS: Dict[str, str] = {
    "bertimbau": BERTIMBAU,
    "xlmr": XLMR,
}

MAX_LENGTH = 256
HEAD_TOKENS = 128
TAIL_TOKENS = 126
DROPOUT = 0.1
LR = 2e-5
WEIGHT_DECAY = 0.01
BATCH_SIZE = 16
MAX_EPOCHS = 10
WARMUP_RATIO = 0.10
PATIENCE = 3
LOGREG_C_GRID: Tuple[float, ...] = (0.25, 1.0, 4.0)
TFIDF_WORD_MAX_FEATURES = 50_000
TFIDF_CHAR_MAX_FEATURES = 40_000

DISPLAY_NAMES: Dict[str, str] = {
    "POS": "Positivo",
    "NEG": "Negativo",
    "NEU": "Neutro",
    "MAJ_POS": "Misto (+)",
    "DIV": "Misto (=)",
    "MAJ_NEG": "Misto (-)",
    "NM": "Não mencionado",
    "MISTO": "Misto",
}


def classes_for_scheme(scheme: str) -> List[str]:
    if scheme == "7":
        return list(CLASSES_7)
    if scheme == "5":
        return list(CLASSES_5)
    if scheme == "binary":
        return list(BINARY_MARKERS)
    raise ValueError(f"Esquema desconhecido: {scheme}")


def map_scheme_label(label: str, scheme: str) -> str:
    if scheme == "7":
        return label
    if scheme == "5":
        return "MISTO" if label in MIXED_7 else label
    raise ValueError("map_scheme_label só vale para esquemas 7 e 5")
