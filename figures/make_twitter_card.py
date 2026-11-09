"""Generate Twitter/X summary card from raw event logs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swarm.config import CHEATER_NAMES, HONEST_LLM_NAMES, SEED_AGENT_NAMES

HONEST = set(HONEST_LLM_NAMES)
CHEATERS = set(CHEATER_NAMES)
SEEDS_SET = set(SEED_AGENT_NAMES)


def load_events(cond: str, seed: int) -> list[dict]:
    if seed < 10:
        return [json.loads(l) for l in open(f"runs/real/{cond}_seed{seed}/events.jsonl")]
    else:
        return [json.loads(l) for l in open(f"runs/followup/qwen_{cond}_seed{seed}/events.jsonl")]


def entry_info(events):
    owners = {}
    for e in events:
        if e["type"] == "submit" and e["payload"].get("accepted"):
            owners[e["payload"]["entry_id"]] = e["agent"]
    ch = {eid for eid, ag in owners.items() if ag in CHEATERS}
    de = {eid for eid, ag in owners.items() if ag in SEEDS_SET}
    ho = {eid for eid, ag in owners.items() if ag in HONEST}
    return ch, de, ho


def first_verdict_rates(events, ch, de, ho):
    first = {}
    for e in events:
        if e["type"] == "review" and e["agent"] in HONEST:
            eid = e["payload"]["entry_id"]
            key = (e["agent"], eid)
            rnd = e["round"]
            if key not in first or rnd < first[key][0]:
                first[key] = (rnd, e["payload"]["verdict"])

    def rate(target_eids):
        total = flags = 0
        for (ag, eid), (rnd, v) in first.items():
            if eid in target_eids:
                total += 1
                if v == "exploit":
                    flags += 1
        return flags, total

    return rate(ch), rate(de), rate(ho)


def per_seed_counts(cond: str, seed_range, category: str) -> list[tuple[int, int]]:
    out = []
    for seed in seed_range:
        events = load_events(cond, seed)
        ch, de, ho = entry_info(events)
        (cf, ct), (df, dt), (hf, ht) = first_verdict_rates(events, ch, de, ho)
        if category == "cheater":
            out.append((cf, ct))
        elif category == "decoy":
            out.append((df, dt))
        else:
            out.append((hf, ht))
    return out


def bootstrap_pooled_ci(counts, n_boot=10000, ci=0.95):
    n = len(counts)
    total_f = sum(f for f, t in counts)
    total_t = sum(t for f, t in counts)
    point = total_f / total_t * 100 if total_t > 0 else 0.0
    rng = np.random.default_rng(42)
    boot_rates = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        bf = sum(counts[i][0] for i in idx)
        bt = sum(counts[i][1] for i in idx)
        boot_rates.append(bf / bt * 100 if bt > 0 else 0.0)
    boot_rates = np.array(boot_rates)
    alpha = (1 - ci) / 2
    return point, float(np.quantile(boot_rates, alpha)), float(np.quantile(boot_rates, 1 - alpha))


def main():
    conditions = ["A", "B", "C"]

    # Pooled decoy rates (seeds 0-9)
    decoy_vals = {}
    for cond in conditions:
        counts = per_seed_counts(cond, range(10), "decoy")
        decoy_vals[cond] = bootstrap_pooled_ci(counts)

    # Pooled honest reference (all conditions, seeds 0-9)
    all_honest_counts = []
    for cond in conditions:
        all_honest_counts.extend(per_seed_counts(cond, range(10), "honest"))
    total_hf = sum(f for f, t in all_honest_counts)
    total_ht = sum(t for f, t in all_honest_counts)
    honest_pct = total_hf / total_ht * 100 if total_ht > 0 else 0.0

    # Figure: 1600x900 at 200 dpi = 8x4.5 inches
    fig = plt.figure(figsize=(8, 4.5), dpi=200, facecolor="white")

    gs = gridspec.GridSpec(3, 2, figure=fig,
                           height_ratios=[0.22, 0.64, 0.14],
                           width_ratios=[0.58, 0.42],
                           hspace=0.22, wspace=0.04,
                           left=0.06, right=0.96, top=0.95, bottom=0.03)

    # --- Headline ---
    ax_head = fig.add_subplot(gs[0, :])
    ax_head.axis("off")
    headline = ("We gave an AI swarm the power to report cheating.\n"
                "A reward meant to keep reports honest made them flag correct work more.")
    ax_head.text(0.5, 0.45, headline, transform=ax_head.transAxes,
                 fontsize=14.5, fontweight="bold", color="#1a1a1a",
                 ha="center", va="center", linespacing=1.35,
                 fontfamily="sans-serif")

    # --- Bar chart (left) ---
    ax = fig.add_subplot(gs[1, 0])

    cond_labels = ["A\nno power", "B\npower", "C\npower + CA"]
    colors = ["#888888", "#AAAAAA", "#009988"]
    edge_colors = ["#666666", "#888888", "#007766"]

    x = np.arange(3)
    bar_vals = [decoy_vals[c][0] for c in conditions]
    bar_lo = [decoy_vals[c][1] for c in conditions]
    bar_hi = [decoy_vals[c][2] for c in conditions]
    err_lo = [v - lo for v, lo in zip(bar_vals, bar_lo)]
    err_hi = [hi - v for v, hi in zip(bar_vals, bar_hi)]

    bars = ax.bar(x, bar_vals, width=0.55, color=colors, edgecolor=edge_colors,
                  linewidth=0.8, yerr=[err_lo, err_hi], capsize=4,
                  error_kw={"linewidth": 1.2, "color": "#444444"})

    # Value labels on bars
    for i, (bar, val) in enumerate(zip(bars, bar_vals)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + err_hi[i] + 1.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=12.5,
                fontweight="bold", color=edge_colors[i])

    # Honest reference line
    ax.axhline(honest_pct, color="#CCCCCC", linewidth=1, linestyle="--", zorder=0)
    ax.text(-0.4, honest_pct + 1.0, f"ordinary honest work: {honest_pct:.0f}%",
            fontsize=8, color="#AAAAAA", ha="left", va="bottom")

    ax.set_xticks(x)
    ax.set_xticklabels(cond_labels, fontsize=10, linespacing=1.1)
    ax.set_ylabel("Flagged as cheating (%)", fontsize=11, labelpad=6)
    ax.set_ylim(0, 68)
    ax.set_xlim(-0.5, 2.7)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_locator(plt.MultipleLocator(10))
    ax.yaxis.grid(True, linewidth=0.3, color="#E0E0E0", zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.spines["left"].set_linewidth(0.5)

    ax.set_title("How often correct but unusual-looking answers\nwere flagged as cheating (10 runs per setup)",
                 fontsize=9.5, pad=8, color="#555555", linespacing=1.3)

    # --- Takeaways (right) ---
    ax_text = fig.add_subplot(gs[1, 1])
    ax_text.axis("off")

    takeaways = [
        ("1.", "Agents noticed cheating\n   but almost never reported\n   it publicly."),
        ("2.", "They judged work by how\n   it looked, not whether\n   it was correct."),
        ("3.", "Rewarding agreement\n   amplified their shared\n   mistake (14 of 20 runs)."),
    ]

    y_start = 0.88
    y_step = 0.32
    for i, (num, text) in enumerate(takeaways):
        y = y_start - i * y_step
        ax_text.text(0.06, y, num, transform=ax_text.transAxes,
                     fontsize=14, fontweight="bold", color="#009988",
                     va="top", ha="right", fontfamily="sans-serif")
        ax_text.text(0.09, y, text, transform=ax_text.transAxes,
                     fontsize=11, color="#333333", va="top",
                     linespacing=1.25, fontfamily="sans-serif")

    # --- Footer ---
    ax_foot = fig.add_subplot(gs[2, :])
    ax_foot.axis("off")
    footer = ("Preliminary: one model (qwen3.5-397b), 50 runs, pre-registered predictions.  "
              "Apart Research Swarm Alignment Hackathon, Nov 2026  ·  @nirdesho6o")
    ax_foot.text(0.5, 0.3, footer, transform=ax_foot.transAxes,
                 fontsize=7.5, color="#AAAAAA", ha="center", va="center",
                 fontfamily="sans-serif")

    fig.savefig("figures/twitter_card.png", dpi=200, bbox_inches="tight",
                facecolor="white", pad_inches=0.15)
    plt.close(fig)

    print("Plotted values (seeds 0-9, POOLED first-verdict decoy flag rate):")
    for cond in conditions:
        pt, lo, hi = decoy_vals[cond]
        counts = per_seed_counts(cond, range(10), "decoy")
        f = sum(ff for ff, tt in counts)
        t = sum(tt for ff, tt in counts)
        print(f"  {cond}: {pt:.1f}% ({f}/{t}) [{lo:.1f}%, {hi:.1f}%]")
    print(f"  Honest reference: {honest_pct:.1f}%")

    return decoy_vals, honest_pct


if __name__ == "__main__":
    decoy_vals, honest_pct = main()

    # Append to figures.md
    lines = [
        "\n## Twitter card: plotted values (seeds 0-9, POOLED first-verdict decoy flag rate)\n",
        "| Condition | Pooled rate (%) | 95% CI |",
        "|-----------|-----------------|--------|",
    ]
    for cond, label in [("A", "A (no power)"), ("B", "B (power)"), ("C", "C (power + CA)")]:
        pt, lo, hi = decoy_vals[cond]
        counts = per_seed_counts(cond, range(10), "decoy")
        f = sum(ff for ff, tt in counts)
        t = sum(tt for ff, tt in counts)
        lines.append(f"| {label} | {pt:.1f}% ({f}/{t}) | [{lo:.1f}%, {hi:.1f}%] |")
    lines.append(f"\nHonest reference line: {honest_pct:.1f}%")

    with open("analysis/figures.md", "a") as f:
        f.write("\n".join(lines) + "\n")
    print("\nAppended to analysis/figures.md")
    print("Saved: figures/twitter_card.png")
