"""Generate report figures from raw event logs."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swarm.config import CHEATER_NAMES, HONEST_LLM_NAMES, SEED_AGENT_NAMES

HONEST = set(HONEST_LLM_NAMES)
CHEATERS = set(CHEATER_NAMES)
SEEDS_SET = set(SEED_AGENT_NAMES)

CB_BLUE = "#0077BB"
CB_ORANGE = "#EE7733"
CB_TEAL = "#009988"
CB_MAGENTA = "#CC3311"
CB_GREY = "#BBBBBB"


def load_events(cond: str, seed: int) -> list[dict]:
    if cond == "D":
        p = Path(f"runs/control/D_seed{seed}/events.jsonl")
    elif seed < 10:
        p = Path(f"runs/real/{cond}_seed{seed}/events.jsonl")
    else:
        p = Path(f"runs/followup/qwen_{cond}_seed{seed}/events.jsonl")
    return [json.loads(l) for l in open(p)]


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


def per_seed_rates(cond: str, seed_range) -> dict[str, list[float | None]]:
    """Return {category: [rate_per_seed]} for first-verdict flag rates."""
    out = {"cheater": [], "decoy": [], "honest": []}
    for seed in seed_range:
        events = load_events(cond, seed)
        ch, de, ho = entry_info(events)
        (cf, ct), (df, dt), (hf, ht) = first_verdict_rates(events, ch, de, ho)
        out["cheater"].append(cf / ct if ct > 0 else None)
        out["decoy"].append(df / dt if dt > 0 else None)
        out["honest"].append(hf / ht if ht > 0 else None)
    return out


def pooled_rate(cond: str, seed_range, category: str) -> tuple[int, int]:
    total_f = total_t = 0
    for seed in seed_range:
        events = load_events(cond, seed)
        ch, de, ho = entry_info(events)
        (cf, ct), (df, dt), (hf, ht) = first_verdict_rates(events, ch, de, ho)
        if category == "cheater":
            total_f += cf; total_t += ct
        elif category == "decoy":
            total_f += df; total_t += dt
        else:
            total_f += hf; total_t += ht
    return total_f, total_t


def bootstrap_ci(rates: list[float | None], n_boot: int = 10000, ci: float = 0.95) -> tuple[float, float, float]:
    valid = [r for r in rates if r is not None]
    if not valid:
        return 0.0, 0.0, 0.0
    arr = np.array(valid)
    rng = np.random.default_rng(42)
    means = np.array([rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n_boot)])
    alpha = (1 - ci) / 2
    lo, hi = np.quantile(means, alpha), np.quantile(means, 1 - alpha)
    return arr.mean(), lo, hi


def per_seed_counts(cond: str, seed_range) -> dict[str, list[tuple[int, int]]]:
    """Return {category: [(flags, total) per seed]} for first-verdict flag counts."""
    out = {"cheater": [], "decoy": [], "honest": []}
    for seed in seed_range:
        events = load_events(cond, seed)
        ch, de, ho = entry_info(events)
        (cf, ct), (df, dt), (hf, ht) = first_verdict_rates(events, ch, de, ho)
        out["cheater"].append((cf, ct))
        out["decoy"].append((df, dt))
        out["honest"].append((hf, ht))
    return out


def bootstrap_pooled_ci(counts: list[tuple[int, int]], n_boot: int = 10000, ci: float = 0.95) -> tuple[float, float, float]:
    """Bootstrap CI for the pooled rate by resampling seeds."""
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


# =====================================================================
# Figure 1: Grouped bar chart, seeds 0-9, POOLED rates
# =====================================================================
def make_fig1():
    conditions = ["A", "B", "C", "D"]
    cond_labels = ["A (no power)", "B (power)", "C (power + CA)", "D (power + flat pay)"]
    categories = ["cheater", "decoy", "honest"]
    cat_labels = ["Cheater\nentries", "Decoys\n(correct, unusual)", "Ordinary\nhonest work"]
    colors = [CB_BLUE, CB_ORANGE, CB_TEAL, CB_MAGENTA]

    data = {}
    ci_data = {}
    for cond in conditions:
        counts = per_seed_counts(cond, range(10))
        for cat in categories:
            point, lo, hi = bootstrap_pooled_ci(counts[cat])
            data[(cond, cat)] = point
            ci_data[(cond, cat)] = (lo, hi)

    fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=300)
    x = np.arange(len(categories))
    n = len(conditions)
    width = 0.18
    offsets = [(i - (n - 1) / 2) * width for i in range(n)]

    for i, (cond, label, color) in enumerate(zip(conditions, cond_labels, colors)):
        vals = [data[(cond, cat)] for cat in categories]
        los = [ci_data[(cond, cat)][0] for cat in categories]
        his = [ci_data[(cond, cat)][1] for cat in categories]
        err_lo = [v - lo for v, lo in zip(vals, los)]
        err_hi = [hi - v for v, hi in zip(vals, his)]
        ax.bar(x + offsets[i], vals, width, label=label, color=color,
               yerr=[err_lo, err_hi], capsize=2, error_kw={"linewidth": 0.8})

    ax.set_ylabel("First-verdict flag rate (%)", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, fontsize=8)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=6, loc="upper right", framealpha=0.9, ncol=2)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig("figures/fig1_flag_rates.pdf", bbox_inches="tight")
    fig.savefig("figures/fig1_flag_rates.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Print values for figures.md
    lines = ["## Figure 1: Pooled first-verdict flag rates (seeds 0-9)\n"]
    lines.append("| Condition | Category | Pooled rate (%) | 95% bootstrap CI |")
    lines.append("|-----------|----------|-----------------|------------------|")
    for cond, clabel in zip(conditions, cond_labels):
        for cat, catlabel in zip(categories, ["Cheater", "Decoy", "Honest"]):
            v = data[(cond, cat)]
            lo, hi = ci_data[(cond, cat)]
            f, t = pooled_rate(cond, range(10), cat)
            lines.append(f"| {clabel} | {catlabel} | {v:.1f}% ({f}/{t}) | [{lo:.1f}%, {hi:.1f}%] |")
    return lines


# =====================================================================
# Figure 2: Paired slope chart, seeds 0-19
# =====================================================================
def make_fig2():
    seed_rates = {}
    for seed in range(20):
        for cond in ["B", "C"]:
            events = load_events(cond, seed)
            ch, de, ho = entry_info(events)
            (_, _), (df, dt), (_, _) = first_verdict_rates(events, ch, de, ho)
            seed_rates[(cond, seed)] = df / dt * 100 if dt > 0 else None

    fig, ax = plt.subplots(figsize=(3.3, 3.5), dpi=300)

    x_left, x_right = 0, 1

    for seed in range(20):
        b_val = seed_rates[("B", seed)]
        c_val = seed_rates[("C", seed)]
        if b_val is None or c_val is None:
            continue

        c_gt_b = c_val > b_val
        color = CB_TEAL if c_gt_b else CB_GREY
        alpha = 0.7 if c_gt_b else 0.4
        lw = 0.8

        if seed < 10:
            marker = "o"
            fillstyle = "full"
            ms = 3.5
        else:
            marker = "o"
            fillstyle = "none"
            ms = 3.5

        ax.plot([x_left, x_right], [b_val, c_val], color=color, alpha=alpha,
                linewidth=lw, zorder=2)
        ax.plot(x_left, b_val, marker=marker, fillstyle=fillstyle, color=color,
                markersize=ms, markeredgewidth=0.8, zorder=3)
        ax.plot(x_right, c_val, marker=marker, fillstyle=fillstyle, color=color,
                markersize=ms, markeredgewidth=0.8, zorder=3)

    # Pooled rates
    b_pooled = 24.5  # from followup.md, verified
    c_pooled = 41.9
    # Recompute to verify
    bf, bt = pooled_rate("B", range(20), "decoy")
    cf, ct = pooled_rate("C", range(20), "decoy")
    b_pooled_check = bf / bt * 100
    c_pooled_check = cf / ct * 100
    print(f"Pooled decoy B: {b_pooled_check:.1f}% ({bf}/{bt}), C: {c_pooled_check:.1f}% ({cf}/{ct})")

    ax.plot([x_left, x_right], [b_pooled_check, c_pooled_check], color=CB_BLUE,
            linewidth=2.5, zorder=4, solid_capstyle="round")
    ax.plot(x_left, b_pooled_check, "s", color=CB_BLUE, markersize=5, zorder=5)
    ax.plot(x_right, c_pooled_check, "s", color=CB_BLUE, markersize=5, zorder=5)

    ax.set_xlim(-0.3, 1.3)
    ax.set_xticks([x_left, x_right])
    ax.set_xticklabels(["B (power)", "C (power + CA)"], fontsize=9)
    ax.set_ylabel("First-verdict decoy flag rate (%)", fontsize=9)
    ax.set_ylim(-2, 85)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_title("Decoy flags rose under correlated\nagreement in 14 of 20 seeds", fontsize=9, pad=8)

    # Legend below plot
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=CB_TEAL, lw=1, marker="o", markersize=4,
               label="C > B (solid = seeds 0–9)"),
        Line2D([0], [0], color=CB_TEAL, lw=1, marker="o", markersize=4,
               fillstyle="none", markeredgewidth=0.8,
               label="C > B (hollow = seeds 10–19)"),
        Line2D([0], [0], color=CB_GREY, lw=1, marker="o", markersize=4,
               alpha=0.5, label="C ≤ B"),
        Line2D([0], [0], color=CB_BLUE, lw=2.5, marker="s", markersize=5,
               label="Pooled rate (all seeds)"),
    ]
    ax.legend(handles=legend_elements, fontsize=6.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=2, framealpha=0.9,
              columnspacing=1.0, handletextpad=0.5)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    fig.savefig("figures/fig2_decoy_by_seed.pdf", bbox_inches="tight")
    fig.savefig("figures/fig2_decoy_by_seed.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    return b_pooled_check, c_pooled_check


# =====================================================================
# Verification
# =====================================================================
def verify():
    mismatches = []

    # Check against exploratory.md section 11 (seeds 0-9)
    expected = {
        ("A", "cheater"): (50, 100),
        ("A", "decoy"): (46, 168),
        ("A", "honest"): (4, 377),
        ("B", "cheater"): (69, 203),
        ("B", "decoy"): (36, 137),
        ("B", "honest"): (2, 420),
        ("C", "cheater"): (74, 205),
        ("C", "decoy"): (60, 134),
        ("C", "honest"): (6, 405),
        ("D", "cheater"): (118, 261),
        ("D", "decoy"): (63, 142),
        ("D", "honest"): (3, 407),
    }
    for (cond, cat), (exp_f, exp_t) in expected.items():
        f, t = pooled_rate(cond, range(10), cat)
        if f != exp_f or t != exp_t:
            mismatches.append(f"  exploratory s11 {cond}/{cat}: expected {exp_f}/{exp_t}, got {f}/{t}")

    # Check against followup.md (seeds 0-19, B and C only)
    expected_fu = {
        ("B", "cheater"): (123, 407),
        ("B", "decoy"): (69, 282),
        ("B", "honest"): (10, 842),
        ("C", "cheater"): (152, 418),
        ("C", "decoy"): (113, 270),
        ("C", "honest"): (11, 779),
    }
    for (cond, cat), (exp_f, exp_t) in expected_fu.items():
        f, t = pooled_rate(cond, range(20), cat)
        if f != exp_f or t != exp_t:
            mismatches.append(f"  followup.md {cond}/{cat}: expected {exp_f}/{exp_t}, got {f}/{t}")

    return mismatches


if __name__ == "__main__":
    print("Verifying numbers...")
    mismatches = verify()
    if mismatches:
        print("MISMATCHES FOUND:")
        for m in mismatches:
            print(m)
    else:
        print("All numbers match exploratory.md section 11 and followup.md.")

    print("\nGenerating Figure 1...")
    fig1_lines = make_fig1()

    print("Generating Figure 2...")
    b_pool, c_pool = make_fig2()

    # Write figures.md
    lines = ["# Figure Data\n"]
    lines.extend(fig1_lines)
    lines.append(f"\n## Figure 2: Pooled decoy rates (seeds 0-19)\n")
    lines.append(f"B pooled: {b_pool:.1f}%, C pooled: {c_pool:.1f}%")
    lines.append(f"\nSeeds where C > B: 14/20")

    with open("analysis/figures.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote analysis/figures.md")
    print("Saved: figures/fig1_flag_rates.{pdf,png}, figures/fig2_decoy_by_seed.{pdf,png}")
