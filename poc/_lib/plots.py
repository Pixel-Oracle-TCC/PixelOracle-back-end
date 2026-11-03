"""Gráficos das POCs. Paleta verde-escuro e roxo, sem o azul/laranja padrão."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

GREEN = "#1B4332"
GREEN_SOFT = "#2D6A4F"
PURPLE = "#5A189A"
PURPLE_SOFT = "#9D4EDD"
INK = "#1C1917"
PAPER = "#FBF8F4"
GRID = "#E7E5E4"


def apply_theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titlecolor": INK,
            "font.size": 10,
            "axes.grid": True,
            "grid.color": GRID,
            "axes.axisbelow": True,
        }
    )


def save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
