"""Draw the paper's Fig. 3 (scale behaviour, labelled by grounded-arm version).

Every value below is copied from EVALUATION.md §6.4-§6.5 or re-derived offline from the
committed traces with the error-analysis module (no model, no database):

    uv --directory backend run python -m aletheia.evaluation.error_analysis \
        --claims data/scifact/claims_dev.jsonl --sample <n> --seed 7 --traces runs/<file>

V1 = original verifier prompt (runs of 11 July 2026); V2 = + span-sufficiency test
(re-runs of 11-17 July 2026). Same seed-7 samples in both versions.

    uv --directory backend run python scripts/paper_fig3_scale.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[2] / "docs" / "figures" / "fig3-scale.pdf"

SCALES = ["8B", "70B", "550B"]

# Grounded-arm accuracy (%) on the seed-7 samples.
V1_ACC = [66.7, 70.0, 73.7]  # groq8b_n30, groq70b_n30, nemotron_ultra_n20 (n=30/30/19)
# The *_newverifier traces of the same three runs (n=29/30/20).
V2_ACC = [72.4, 66.7, 70.0]
# Single-LLM baseline accuracy (%) on the V1 samples (EVALUATION.md §6.4).
V1_BASE = [56.7, 80.0, 89.5]

# False grounding: gold NotEnoughInfo claims on which the grounded arm asserted anyway.
V1_FG = [(6, 11), (4, 11), (1, 6)]
V2_FG = [(4, 10), (2, 11), (2, 7)]

BLUE, GREEN, AMBER = "#2a78d6", "#1aa874", "#d98a1c"


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#888888",
            "pdf.fonttype": 42,
        }
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.55, 2.6))
    x = range(len(SCALES))

    ax1.plot(x, V1_BASE, "-o", color=BLUE, lw=2, ms=6, label="Baseline (V1 samples)")
    ax1.plot(x, V1_ACC, "-o", color=GREEN, lw=2, ms=6, label="Grounded, V1")
    ax1.plot(x, V2_ACC, "--s", color=AMBER, lw=2, ms=5, label="Grounded, V2")
    # Per-point label offsets (points above/below) so no two labels collide.
    offsets = {
        "base": (-4.6, 2.2, 2.2),
        "v1": (-4.6, 2.0, 2.0),
        "v2": (2.2, -4.6, -4.6),
    }
    for key, ys in (("base", V1_BASE), ("v1", V1_ACC), ("v2", V2_ACC)):
        for xi, yi, dy in zip(x, ys, offsets[key], strict=True):
            ax1.annotate(f"{yi:.1f}", (xi, yi + dy), ha="center", fontsize=7.5, color="#444444")
    ax1.set_xticks(list(x), SCALES)
    ax1.set_ylim(38, 95)
    ax1.set_ylabel("Verification accuracy (%)")
    ax1.set_xlabel("Base model  ·  n = 30 / 30 / 19\N{EN DASH}20")
    ax1.set_title("(a) Grounded accuracy: rises under V1 only", fontsize=9.5)
    ax1.grid(axis="y", color="#e2e2e2", lw=0.8)
    ax1.legend(frameon=False, fontsize=7.5, loc="lower right")

    width = 0.38
    for offset, data, color, label in (
        (-width / 2, V1_FG, GREEN, "V1"),
        (width / 2, V2_FG, AMBER, "V2"),
    ):
        shares = [100 * a / b for a, b in data]
        xs = [i + offset for i in x]
        ax2.bar(xs, shares, width=width, color=color, label=label)
        for xi, (a, b), s in zip(xs, data, shares, strict=True):
            ax2.annotate(f"{a}/{b}", (xi, s + 1.5), ha="center", fontsize=7.5, color="#444444")
    ax2.set_xticks(list(x), SCALES)
    ax2.set_ylim(0, 65)
    ax2.set_ylabel("False grounding (% of NEI)")
    ax2.set_xlabel("Base model  ·  same seed-7 samples")
    ax2.set_title("(b) False grounding by version", fontsize=9.5)
    ax2.grid(axis="y", color="#e2e2e2", lw=0.8)
    ax2.legend(frameon=False, fontsize=7.5)

    fig.tight_layout()
    fig.savefig(OUT)
    fig.savefig(OUT.with_name("fig3-scale-1.png"), dpi=220)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
