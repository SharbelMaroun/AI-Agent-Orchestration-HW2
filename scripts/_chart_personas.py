"""Per-dimension persona charts: grouped-bar averages + radar."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DIMENSIONS = ["structure", "logos", "pathos", "ethos", "clash"]
COLOR_DOGS, COLOR_CATS = "#3b6e8f", "#bf6f4a"


def _persona_averages(results):
    sums = {"dogs": defaultdict(float), "cats": defaultdict(float)}
    counts = {"dogs": 0, "cats": 0}
    for r in results:
        for s in r.scores:
            for d in DIMENSIONS:
                sums[s.side][d] += getattr(s, d)
            counts[s.side] += 1
    dogs = [sums["dogs"][d] / counts["dogs"] for d in DIMENSIONS]
    cats = [sums["cats"][d] / counts["cats"] for d in DIMENSIONS]
    return dogs, cats


def dimension_averages(results, out: Path) -> None:
    dogs, cats = _persona_averages(results)
    x, w = np.arange(len(DIMENSIONS)), 0.35
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(x - w / 2, dogs, w, label="Dogs", color=COLOR_DOGS)
    ax.bar(x + w / 2, cats, w, label="Cats", color=COLOR_CATS)
    ax.set_xticks(x)
    ax.set_xticklabels(DIMENSIONS)
    ax.set_ylabel("Average score (0-3)")
    ax.set_ylim(0, 3.2)
    ax.legend()
    ax.set_title(f"Average per-dimension score across all {len(results)} debates")
    for i, (d, c) in enumerate(zip(dogs, cats, strict=True)):
        ax.text(i - w / 2, d + 0.05, f"{d:.2f}", ha="center", fontsize=8)
        ax.text(i + w / 2, c + 0.05, f"{c:.2f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def per_dimension_radar(results, out: Path) -> None:
    dogs, cats = _persona_averages(results)
    dogs = [*dogs, dogs[0]]
    cats = [*cats, cats[0]]
    angles = np.linspace(0, 2 * np.pi, len(DIMENSIONS) + 1)
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": "polar"})
    ax.plot(angles, dogs, "o-", color=COLOR_DOGS, label="Dogs", linewidth=2)
    ax.fill(angles, dogs, color=COLOR_DOGS, alpha=0.15)
    ax.plot(angles, cats, "s-", color=COLOR_CATS, label="Cats", linewidth=2)
    ax.fill(angles, cats, color=COLOR_CATS, alpha=0.15)
    ax.set_thetagrids(np.degrees(angles[:-1]), [d.title() for d in DIMENSIONS])
    ax.set_ylim(0, 3)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    ax.set_title("Persona footprint — pathos lean for Cats, logos/ethos lean for Dogs", pad=20)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
