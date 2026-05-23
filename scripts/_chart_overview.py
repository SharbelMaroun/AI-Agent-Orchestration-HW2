"""Outcome-overview charts: win pie + margin bar."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_DOGS, COLOR_CATS = "#3b6e8f", "#bf6f4a"


def win_record(results, out: Path) -> None:
    winners = [r.verdict.winner for r in results]
    d, c = winners.count("dogs"), winners.count("cats")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        [d, c],
        labels=[f"Dogs ({d})", f"Cats ({c})"],
        colors=[COLOR_DOGS, COLOR_CATS],
        autopct="%1.0f%%",
        startangle=90,
    )
    ax.set_title(f"Wins across {len(results)} debates")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def margin_distribution(results, out: Path) -> None:
    xs = list(range(1, len(results) + 1))
    margins = [r.verdict.margin for r in results]
    colors = [COLOR_DOGS if r.verdict.winner == "dogs" else COLOR_CATS for r in results]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(xs, margins, color=colors, edgecolor="black", linewidth=0.5)
    for i, (m, w) in enumerate(zip(margins, [r.verdict.winner for r in results], strict=True)):
        ax.text(i + 1, m + 0.2, w, ha="center", fontsize=9)
    ax.set_xlabel("Debate #")
    ax.set_ylabel("Margin (points)")
    ax.set_title("Victory margin per debate (colour = winner)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
