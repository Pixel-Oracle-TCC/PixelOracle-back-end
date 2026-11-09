"""Encoder compartilhado + 4 cabeças (ou 12 binárias) para sentimento por eixo."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

from config import (
    AXES,
    BATCH_SIZE,
    BINARY_MARKERS,
    CHECKPOINTS_DIR,
    CLASSES_5,
    CLASSES_7,
    DROPOUT,
    HEAD_TOKENS,
    LR,
    MAX_EPOCHS,
    MAX_LENGTH,
    PATIENCE,
    TAIL_TOKENS,
    TEXT_COL,
    WARMUP_RATIO,
    WEIGHT_DECAY,
    map_scheme_label,
)
from metrics import evaluate_multiclass_axes, macro_f1

logger = logging.getLogger(__name__)


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def class_weights(labels: Sequence[str], classes: Sequence[str]) -> torch.Tensor:
    counts = {c: 0 for c in classes}
    for lab in labels:
        if lab in counts:
            counts[lab] += 1
    n = max(len(labels), 1)
    k = len(classes)
    weights = []
    for c in classes:
        freq = counts[c]
        weights.append((n / (k * freq)) if freq > 0 else 0.0)
    tensor = torch.tensor(weights, dtype=torch.float32)
    total = float(tensor.sum())
    if total > 0:
        tensor = tensor * (k / total)
    return tensor


def binary_pos_weight(y: Sequence[int]) -> torch.Tensor:
    pos = max(int(sum(y)), 0)
    neg = max(len(y) - pos, 0)
    if pos == 0:
        return torch.tensor([1.0], dtype=torch.float32)
    return torch.tensor([neg / pos], dtype=torch.float32)


def encode_head_tail(
    tokenizer,
    text: str,
    *,
    max_length: int = MAX_LENGTH,
    head_tokens: int = HEAD_TOKENS,
    tail_tokens: int = TAIL_TOKENS,
) -> Dict[str, List[int]]:
    """Mantém cabeça + cauda quando o texto passa de max_length."""
    ids = tokenizer.encode(text, add_special_tokens=False, truncation=False)
    special = tokenizer.num_special_tokens_to_add(pair=False)
    budget = max_length - special
    if len(ids) > budget:
        ids = ids[:head_tokens] + ids[-tail_tokens:]
    wrapped = tokenizer.prepare_for_model(
        ids,
        max_length=max_length,
        truncation=True,
        padding="max_length",
        return_tensors=None,
    )
    return {
        "input_ids": wrapped["input_ids"],
        "attention_mask": wrapped["attention_mask"],
    }


class ReviewDataset(Dataset):
    def __init__(
        self,
        frame: pd.DataFrame,
        tokenizer,
        *,
        scheme: str,
        label_to_id: Optional[Dict[str, int]] = None,
        max_length: int = MAX_LENGTH,
    ) -> None:
        self.texts = frame[TEXT_COL].astype(str).tolist()
        self.tokenizer = tokenizer
        self.scheme = scheme
        self.label_to_id = label_to_id or {}
        self.max_length = max_length
        self.head_tokens = min(HEAD_TOKENS, max(8, max_length // 2 - 2))
        self.tail_tokens = min(TAIL_TOKENS, max(8, max_length - self.head_tokens - 2))
        if scheme == "binary":
            self.targets = []
            for _, row in frame.iterrows():
                vec: List[int] = []
                for axis in AXES:
                    code = str(row[axis])
                    vec.extend(
                        [
                            int(code != "NM"),
                            int(code in {"POS", "MAJ_POS", "DIV", "MAJ_NEG"}),
                            int(code in {"NEG", "MAJ_POS", "DIV", "MAJ_NEG"}),
                        ]
                    )
                self.targets.append(vec)
        else:
            self.targets = []
            for _, row in frame.iterrows():
                self.targets.append(
                    [self.label_to_id[map_scheme_label(str(row[axis]), scheme)] for axis in AXES]
                )

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        enc = encode_head_tail(
            self.tokenizer,
            self.texts[idx],
            max_length=self.max_length,
            head_tokens=self.head_tokens,
            tail_tokens=self.tail_tokens,
        )
        item = {
            "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(enc["attention_mask"], dtype=torch.long),
        }
        dtype = torch.float32 if self.scheme == "binary" else torch.long
        item["labels"] = torch.tensor(self.targets[idx], dtype=dtype)
        return item


class MultiHeadSentiment(nn.Module):
    def __init__(
        self,
        model_name: str,
        *,
        n_labels: int,
        scheme: str,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        self.scheme = scheme
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden = int(self.encoder.config.hidden_size)
        self.dropout = nn.Dropout(dropout)
        if scheme == "binary":
            self.heads = nn.ModuleList([nn.Linear(hidden, 1) for _ in range(len(AXES) * 3)])
        else:
            self.heads = nn.ModuleList([nn.Linear(hidden, n_labels) for _ in AXES])

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> List[torch.Tensor]:
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = self.dropout(out.last_hidden_state[:, 0])
        return [head(cls) for head in self.heads]


def _logits_to_pred(logits: List[torch.Tensor], scheme: str, id_to_label: Dict[int, str]) -> Dict[str, List[str]]:
    preds: Dict[str, List[str]] = {axis: [] for axis in AXES}
    if scheme == "binary":
        for axis in AXES:
            for marker in BINARY_MARKERS:
                preds[f"{axis}:{marker}"] = []
        batch = logits[0].shape[0]
        for b in range(batch):
            for i, axis in enumerate(AXES):
                for j, marker in enumerate(BINARY_MARKERS):
                    logit = logits[i * 3 + j][b]
                    bit = int(torch.sigmoid(logit).item() >= 0.5)
                    preds[f"{axis}:{marker}"].append(str(bit))
        return preds
    for i, axis in enumerate(AXES):
        idx = torch.argmax(logits[i], dim=-1).tolist()
        preds[axis] = [id_to_label[int(x)] for x in idx]
    return preds


def _val_macro_f1(
    model: MultiHeadSentiment,
    loader: DataLoader,
    device: torch.device,
    scheme: str,
    labels: Sequence[str],
    id_to_label: Dict[int, str],
    val_frame: pd.DataFrame,
) -> float:
    model.eval()
    collected: Dict[str, List[str]] = {axis: [] for axis in AXES}
    if scheme == "binary":
        collected = {f"{axis}:{m}": [] for axis in AXES for m in BINARY_MARKERS}
    with torch.no_grad():
        for batch in loader:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            logits = model(ids, mask)
            chunk = _logits_to_pred(logits, scheme, id_to_label)
            for key, values in chunk.items():
                collected[key].extend(values)
    if scheme == "binary":
        scores = []
        for axis in AXES:
            gold = val_frame[axis].astype(str).tolist()
            y_m = [int(c != "NM") for c in gold]
            y_e = [int(c in {"POS", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in gold]
            y_c = [int(c in {"NEG", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in gold]
            for marker, y in zip(BINARY_MARKERS, (y_m, y_e, y_c)):
                p = [int(x) for x in collected[f"{axis}:{marker}"]]
                scores.append(float(f1_score(y, p, zero_division=0)))
        return float(np.mean(scores)) if scores else 0.0
    f1s = []
    for axis in AXES:
        y_true = [map_scheme_label(str(v), scheme) for v in val_frame[axis].tolist()]
        f1s.append(macro_f1(y_true, collected[axis], labels))
    return float(np.mean(f1s)) if f1s else 0.0


@dataclass
class TrainResult:
    model: MultiHeadSentiment
    tokenizer: object
    id_to_label: Dict[int, str]
    label_to_id: Dict[str, int]
    best_val_f1: float
    checkpoint: Path
    max_length: int = MAX_LENGTH


def train_transformer(
    train: pd.DataFrame,
    val: pd.DataFrame,
    *,
    model_key: str,
    model_name: str,
    scheme: str,
    seed: int,
    smoke: bool = False,
    epochs: Optional[int] = None,
) -> TrainResult:
    set_seeds(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        logger.warning("Sem GPU CUDA — treino em CPU (lento). Use --smoke para validar o pipeline.")

    labels = list(CLASSES_7 if scheme == "7" else CLASSES_5) if scheme != "binary" else ["0", "1"]
    label_to_id = {c: i for i, c in enumerate(labels)} if scheme != "binary" else {}
    id_to_label = {i: c for c, i in label_to_id.items()}

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    n_out = 1 if scheme == "binary" else len(labels)
    model = MultiHeadSentiment(model_name, n_labels=max(n_out, 2), scheme=scheme).to(device)

    max_length = 64 if smoke else MAX_LENGTH
    if smoke:
        batch_size = 2
    elif device.type != "cuda":
        batch_size = min(4, BATCH_SIZE)
        logger.warning("CPU: batch=%s, max_length=%s", batch_size, max_length)
    else:
        batch_size = BATCH_SIZE
    train_ds = ReviewDataset(
        train, tokenizer, scheme=scheme, label_to_id=label_to_id, max_length=max_length
    )
    val_ds = ReviewDataset(
        val, tokenizer, scheme=scheme, label_to_id=label_to_id, max_length=max_length
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    n_labels = len(labels) if scheme != "binary" else 2
    if scheme == "binary":
        criteria = []
        gold_cols = []
        for axis in AXES:
            codes = train[axis].astype(str).tolist()
            gold_cols.append([int(c != "NM") for c in codes])
            gold_cols.append([int(c in {"POS", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in codes])
            gold_cols.append([int(c in {"NEG", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in codes])
        for y in gold_cols:
            pw = binary_pos_weight(y).to(device)
            criteria.append(nn.BCEWithLogitsLoss(pos_weight=pw))
    else:
        criteria = []
        for axis in AXES:
            y = [map_scheme_label(str(v), scheme) for v in train[axis].tolist()]
            w = class_weights(y, labels).to(device)
            criteria.append(nn.CrossEntropyLoss(weight=w))

    optim = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    n_epochs = 1 if smoke else (epochs or MAX_EPOCHS)
    total_steps = max(len(train_loader) * n_epochs, 1)
    warmup = int(total_steps * WARMUP_RATIO)
    sched = get_linear_schedule_with_warmup(optim, warmup, total_steps)
    use_fp16 = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_fp16)

    ckpt_dir = CHECKPOINTS_DIR / f"{model_key}_{scheme}_seed{seed}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    best_path = ckpt_dir / "best.pt"
    best_f1 = -1.0
    stale = 0

    for epoch in range(1, n_epochs + 1):
        model.train()
        running = 0.0
        bar = tqdm(train_loader, desc=f"{model_key} {scheme} ep{epoch}", leave=False)
        for batch in bar:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            y = batch["labels"].to(device)
            optim.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_fp16):
                logits = model(ids, mask)
                if scheme == "binary":
                    loss = sum(
                        crit(logit.squeeze(-1), y[:, i].float())
                        for i, (crit, logit) in enumerate(zip(criteria, logits))
                    )
                else:
                    loss = sum(crit(logit, y[:, i]) for i, (crit, logit) in enumerate(zip(criteria, logits)))
            scaler.scale(loss).backward()
            scaler.step(optim)
            scaler.update()
            sched.step()
            running += float(loss.item())
            bar.set_postfix(loss=f"{running / max(bar.n, 1):.3f}")

        val_f1 = _val_macro_f1(model, val_loader, device, scheme, labels, id_to_label, val)
        logger.info("epoch %s val macro-F1 médio=%.4f", epoch, val_f1)
        if val_f1 > best_f1:
            best_f1 = val_f1
            stale = 0
            torch.save(
                {
                    "model": model.state_dict(),
                    "scheme": scheme,
                    "model_name": model_name,
                    "label_to_id": label_to_id,
                    "val_f1": best_f1,
                },
                best_path,
            )
        else:
            stale += 1
            if stale >= PATIENCE:
                logger.info("early stopping na época %s", epoch)
                break

    blob = torch.load(best_path, map_location=device)
    model.load_state_dict(blob["model"])
    return TrainResult(
        model=model,
        tokenizer=tokenizer,
        id_to_label=id_to_label,
        label_to_id=label_to_id,
        best_val_f1=best_f1,
        checkpoint=best_path,
        max_length=max_length,
    )


def predict_transformer(
    result: TrainResult,
    frame: pd.DataFrame,
    *,
    scheme: str,
    batch_size: int = BATCH_SIZE,
) -> Dict[str, List[str]]:
    device = next(result.model.parameters()).device
    ds = ReviewDataset(
        frame,
        result.tokenizer,
        scheme=scheme,
        label_to_id=result.label_to_id,
        max_length=result.max_length,
    )
    eval_bs = 2 if result.max_length <= 64 else batch_size
    loader = DataLoader(ds, batch_size=eval_bs)
    result.model.eval()
    collected: Dict[str, List[str]] = {axis: [] for axis in AXES}
    if scheme == "binary":
        collected = {f"{axis}:{m}": [] for axis in AXES for m in BINARY_MARKERS}
    with torch.no_grad():
        for batch in loader:
            ids = batch["input_ids"].to(device)
            mask = batch["attention_mask"].to(device)
            logits = result.model(ids, mask)
            chunk = _logits_to_pred(logits, scheme, result.id_to_label)
            for key, values in chunk.items():
                collected[key].extend(values)
    return collected


def evaluate_transformer(
    result: TrainResult,
    test: pd.DataFrame,
    *,
    scheme: str,
    stem_prefix: str,
) -> Dict[str, Dict[str, float]]:
    preds = predict_transformer(result, test, scheme=scheme)
    if scheme == "binary":
        summary: Dict[str, Dict[str, float]] = {}
        for axis in AXES:
            codes = test[axis].astype(str).tolist()
            gold = {
                "mencionado": [int(c != "NM") for c in codes],
                "elogio": [int(c in {"POS", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in codes],
                "critica": [int(c in {"NEG", "MAJ_POS", "DIV", "MAJ_NEG"}) for c in codes],
            }
            axis_scores = {}
            for marker in BINARY_MARKERS:
                p = [int(x) for x in preds[f"{axis}:{marker}"]]
                axis_scores[marker] = float(f1_score(gold[marker], p, zero_division=0))
            axis_scores["macro_f1"] = float(np.mean(list(axis_scores.values())))
            summary[axis] = axis_scores
        summary["_mean"] = {"macro_f1": float(np.mean([summary[a]["macro_f1"] for a in AXES]))}
        return summary
    labels = list(CLASSES_7 if scheme == "7" else CLASSES_5)
    true_by = {
        axis: [map_scheme_label(str(v), scheme) for v in test[axis].tolist()] for axis in AXES
    }
    return evaluate_multiclass_axes(true_by, preds, labels, stem_prefix=stem_prefix)
