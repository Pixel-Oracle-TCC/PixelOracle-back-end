"""Split por game_id sem vazamento de jogo nem de texto."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data import split_by_game  # noqa: E402


def _toy(n_games: int = 12, per: int = 5) -> pd.DataFrame:
    rows = []
    labels = ["POS", "NEG", "NEU", "NM", "DIV"]
    for g in range(n_games):
        for i in range(per):
            lab = labels[(g + i) % len(labels)]
            rows.append(
                {
                    "game_id": g,
                    "texto": f"review do jogo {g} item {i}",
                    "Mecânica": lab,
                    "Narrativa": lab,
                    "Estética": lab,
                    "Tecnologia": lab,
                }
            )
    return pd.DataFrame(rows)


def test_no_game_overlap() -> None:
    split = split_by_game(_toy())
    ids = {k: set(split.game_ids[k]) for k in ("train", "val", "test")}
    assert not ids["train"] & ids["val"]
    assert not ids["train"] & ids["test"]
    assert not ids["val"] & ids["test"]
    assert len(split.train) + len(split.val) + len(split.test) == 60


def test_same_text_same_game_stays_together() -> None:
    frame = _toy(6, 4)
    split = split_by_game(frame)
    for _, row in frame.iterrows():
        gid = row["game_id"]
        bucket = None
        for name, ids in split.game_ids.items():
            if gid in ids:
                bucket = name
        assert bucket is not None
        part = getattr(split, bucket)
        assert set(part.loc[part["game_id"] == gid, "texto"]) <= set(
            frame.loc[frame["game_id"] == gid, "texto"]
        )


if __name__ == "__main__":
    test_no_game_overlap()
    test_same_text_same_game_stays_together()
    print("ok test_split")
