"""Time-series + economy charts: score evolution, token + cost, citation density."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLOR_DOGS, COLOR_CATS = "#3b6e8f", "#bf6f4a"


def score_evolution(results, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4))
    for r in results:
        rounds = sorted({s.ping_round for s in r.scores})
        ds, cs = 0, 0
        dogs_cum, cats_cum = [], []
        for rd in rounds:
            for s in r.scores:
                if s.ping_round == rd:
                    val = s.structure + s.logos + s.pathos + s.ethos + s.clash
                    if s.side == "dogs":
                        ds += val
                    else:
                        cs += val
            dogs_cum.append(ds)
            cats_cum.append(cs)
        ax.plot(rounds, dogs_cum, color=COLOR_DOGS, alpha=0.5, linewidth=1)
        ax.plot(rounds, cats_cum, color=COLOR_CATS, alpha=0.5, linewidth=1)
    ax.plot([], [], color=COLOR_DOGS, label="Dogs cumulative")
    ax.plot([], [], color=COLOR_CATS, label="Cats cumulative")
    ax.set_xlabel("Round")
    ax.set_ylabel("Cumulative score")
    ax.legend()
    ax.set_title(f"Cumulative score per round — {len(results)} debates overlaid")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def token_and_cost(results, out: Path) -> None:
    xs = list(range(1, len(results) + 1))
    tokens_in = [sum(p.tokens_in for p in r.pings) for r in results]
    tokens_out = [sum(p.tokens_out for p in r.pings) for r in results]
    costs = [r.cost_report.get("total_usd", 0.0) if r.cost_report else 0.0 for r in results]
    fig, ax1 = plt.subplots(figsize=(8, 4))
    w = 0.35
    ax1.bar([x - w / 2 for x in xs], tokens_in, w, label="Input tokens", color="#5b8db8")
    ax1.bar([x + w / 2 for x in xs], tokens_out, w, label="Output tokens", color="#e9b984")
    ax1.set_xlabel("Debate #")
    ax1.set_ylabel("Tokens")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(xs, costs, "o-", color="black", label="Cost (USD)")
    ax2.set_ylabel("Cost (USD)")
    ax2.legend(loc="upper right")
    ax1.set_title("Token economy & cost per debate")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def citation_density(results, out: Path) -> None:
    dogs = [len(p.citations) for r in results for p in r.pings if p.side == "dogs"]
    cats = [len(p.citations) for r in results for p in r.pings if p.side == "cats"]
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.arange(0, max(max(dogs, default=0), max(cats, default=0)) + 2) - 0.5
    ax.hist(
        dogs,
        bins=bins,
        alpha=0.6,
        label=f"Dogs (n={len(dogs)})",
        color=COLOR_DOGS,
        edgecolor="black",
    )
    ax.hist(
        cats,
        bins=bins,
        alpha=0.6,
        label=f"Cats (n={len(cats)})",
        color=COLOR_CATS,
        edgecolor="black",
    )
    ax.set_xlabel("Citations per ping")
    ax.set_ylabel("Number of pings")
    ax.legend()
    ax.set_title(f"Citation density — {len(results)} debates")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
