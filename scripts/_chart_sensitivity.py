"""Chart helpers for the sensitivity study. Split from the runner script to
keep each file under the 150-LOC cap (CLAUDE.md §4). Each function takes a
report/stats object + an output Path and writes one high-resolution PNG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from debate.services.analysis import SensitivityReport, predict_economics
from debate.shared.config import SetupConfig

DOGS_BLUE = "#3b6e8f"
CATS_ORANGE = "#bf6f4a"
DPI = 150


def tornado(report: SensitivityReport, path: Path) -> None:
    """Horizontal bar of each factor's metric range — the importance ranking."""
    factors = list(reversed(report.factors))  # largest on top
    names = [f.factor for f in factors]
    ranges = [f.metric_range for f in factors]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(names, ranges, color=DOGS_BLUE)
    ax.set_xlabel(f"Range of {report.metric} across swept levels")
    ax.set_title(f"Tornado — factor influence on {report.metric} (OAT)")
    for i, val in enumerate(ranges):
        ax.text(val, i, f" {val:.4g}", va="center")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def factor_lines(report: SensitivityReport, path: Path) -> None:
    """Small-multiples: target metric vs each numeric factor's levels."""
    numeric = [f for f in report.factors if all(isinstance(p.level, int | float) for p in f.points)]
    fig, axes = plt.subplots(1, len(numeric), figsize=(4 * len(numeric), 3.2), squeeze=False)
    for ax, f in zip(axes[0], numeric, strict=False):
        xs = [p.level for p in f.points]
        ys = [p.metrics[report.metric] for p in f.points]
        ax.plot(xs, ys, marker="o", color=CATS_ORANGE)
        el = f"elasticity {f.elasticity:+.2f}" if f.elasticity is not None else ""
        ax.set_title(f"{f.factor}\n{el}")
        ax.set_xlabel(f.factor)
        ax.set_ylabel(report.metric)
        ax.grid(True, alpha=0.3)
    fig.suptitle(f"OAT response of {report.metric}")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def interaction_heatmap(setup: SetupConfig, path: Path) -> None:
    """2-factor heatmap: cost over the num_rounds × max_words_per_ping grid."""
    cfg = setup.analysis
    rounds = [int(r) for r in cfg.factors["num_rounds"]]
    words = [int(w) for w in cfg.factors["max_words_per_ping"]]
    grid = [
        [
            predict_economics(
                num_rounds=r,
                max_words_per_ping=w,
                model=cfg.baseline.model,
                cache_read_pct=cfg.baseline.cache_read_pct,
                token_model=cfg.token_model,
                pricing=setup.pricing,
            ).cost_usd
            for r in rounds
        ]
        for w in words
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(grid, cmap="viridis", origin="lower", aspect="auto")
    ax.set_xticks(range(len(rounds)), rounds)
    ax.set_yticks(range(len(words)), words)
    ax.set_xlabel("num_rounds")
    ax.set_ylabel("max_words_per_ping")
    ax.set_title("Predicted cost (USD) — rounds × words interaction")
    fig.colorbar(im, ax=ax, label="cost_usd")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def empirical_boxplots(stats, path: Path) -> None:
    """Box plots of observed rubric-dimension scores (built from the recorded
    debates' five-number summaries via ``ax.bxp``)."""

    def _bx(dist) -> dict:
        return {
            "label": dist.name,
            "med": dist.median,
            "q1": dist.q1,
            "q3": dist.q3,
            "whislo": dist.minimum,
            "whishi": dist.maximum,
            "fliers": [],
        }

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bxp([_bx(d) for d in stats.dimensions.values()], showfliers=False)
    ax.set_ylabel("Per-ping score (0–3)")
    ax.set_title(f"Observed rubric-dimension spread across {stats.n_debates} debates")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
