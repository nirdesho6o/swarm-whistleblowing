"""Exploratory analyses on runs/real. No changes to definitions."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm.config import CHEATER_NAMES, HONEST_LLM_NAMES, SEED_AGENT_NAMES
from analysis.metrics import compute_monitor_metrics

CHEATERS = set(CHEATER_NAMES)
HONEST = set(HONEST_LLM_NAMES)
SEEDS_SET = set(SEED_AGENT_NAMES)
CONDITIONS = ["A", "B", "C"]
SEED_RANGE = range(10)


def load_run(cond: str, seed: int) -> list[dict]:
    return [json.loads(l) for l in open(f"runs/real/{cond}_seed{seed}/events.jsonl")]


def fmt(val, pct=False):
    if val is None:
        return "N/A"
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return str(val)
    if pct:
        return f"{val*100:.1f}%"
    if isinstance(val, float):
        return f"{val:.3f}"
    return str(val)


def entry_info(events):
    entries = {}
    for e in events:
        if e["type"] == "submit" and e["payload"].get("accepted"):
            entries[e["payload"]["entry_id"]] = {
                "agent": e["agent"],
                "via_exploit": e["payload"]["via_exploit"],
            }
    cheater_eids = {eid for eid, info in entries.items() if info["agent"] in CHEATERS}
    honest_eids = {eid for eid, info in entries.items() if info["agent"] in HONEST}
    decoy_eids = {eid for eid, info in entries.items() if info["agent"] in SEEDS_SET}
    return entries, cheater_eids, honest_eids, decoy_eids


def main():
    lines = []
    lines.append("# Exploratory Analyses\n")

    # ================================================================
    # 1. Per condition: cheater flag rate, TPR/FPR/AUROC
    # ================================================================
    lines.append("## 1. Flag rates and swarm-as-monitor metrics per condition\n")
    lines.append("### Cheater flag rate per run\n")
    lines.append("| Run | Cheater flag% | Decoy flag% | Honest flag% |")
    lines.append("|-----|---------------|-------------|--------------|")

    cond_cheater_flags = {c: 0 for c in CONDITIONS}
    cond_cheater_reviews = {c: 0 for c in CONDITIONS}
    cond_decoy_flags = {c: 0 for c in CONDITIONS}
    cond_decoy_reviews = {c: 0 for c in CONDITIONS}
    cond_honest_flags = {c: 0 for c in CONDITIONS}
    cond_honest_reviews = {c: 0 for c in CONDITIONS}

    for cond in CONDITIONS:
        for seed in SEED_RANGE:
            events = load_run(cond, seed)
            _, cheater_eids, honest_eids, decoy_eids = entry_info(events)
            cf = cr = df = dr = hf = hr = 0
            for e in events:
                if e["type"] == "review" and e["agent"] in HONEST:
                    eid = e["payload"]["entry_id"]
                    v = e["payload"]["verdict"]
                    if eid in cheater_eids:
                        cr += 1
                        if v == "exploit": cf += 1
                    elif eid in decoy_eids:
                        dr += 1
                        if v == "exploit": df += 1
                    elif eid in honest_eids:
                        hr += 1
                        if v == "exploit": hf += 1
            cond_cheater_flags[cond] += cf
            cond_cheater_reviews[cond] += cr
            cond_decoy_flags[cond] += df
            cond_decoy_reviews[cond] += dr
            cond_honest_flags[cond] += hf
            cond_honest_reviews[cond] += hr
            cfr = cf/cr if cr > 0 else None
            dfr = df/dr if dr > 0 else None
            hfr = hf/hr if hr > 0 else None
            lines.append(f"| {cond}_seed{seed} | {fmt(cfr, True)} | {fmt(dfr, True)} | {fmt(hfr, True)} |")

    lines.append("\n### Aggregate flag rates\n")
    lines.append("| Condition | Cheater flag% | Decoy flag% | Honest flag% |")
    lines.append("|-----------|---------------|-------------|--------------|")
    for c in CONDITIONS:
        cfr = cond_cheater_flags[c]/cond_cheater_reviews[c] if cond_cheater_reviews[c] > 0 else None
        dfr = cond_decoy_flags[c]/cond_decoy_reviews[c] if cond_decoy_reviews[c] > 0 else None
        hfr = cond_honest_flags[c]/cond_honest_reviews[c] if cond_honest_reviews[c] > 0 else None
        lines.append(f"| {c} | {fmt(cfr, True)} | {fmt(dfr, True)} | {fmt(hfr, True)} |")

    lines.append("\n### Swarm-as-monitor (TPR/FPR/AUROC) per run\n")
    lines.append("| Run | TPR | FPR | AUROC |")
    lines.append("|-----|-----|-----|-------|")
    cond_monitor = {c: {"tpr": [], "fpr": [], "auroc": []} for c in CONDITIONS}
    for cond in CONDITIONS:
        for seed in SEED_RANGE:
            events = load_run(cond, seed)
            mm = compute_monitor_metrics(events, rng_seed=seed)
            lines.append(f"| {cond}_seed{seed} | {fmt(mm['swarm_tpr'], True)} | {fmt(mm['swarm_fpr'], True)} | {fmt(mm['swarm_auroc'])} |")
            for k in ("tpr", "fpr", "auroc"):
                v = mm[f"swarm_{k}"]
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    cond_monitor[cond][k].append(v)

    lines.append("\n### Aggregate swarm-as-monitor\n")
    lines.append("| Condition | Mean TPR | Mean FPR | Mean AUROC |")
    lines.append("|-----------|----------|----------|------------|")
    for c in CONDITIONS:
        def mean(lst):
            return sum(lst)/len(lst) if lst else None
        lines.append(f"| {c} | {fmt(mean(cond_monitor[c]['tpr']), True)} | {fmt(mean(cond_monitor[c]['fpr']), True)} | {fmt(mean(cond_monitor[c]['auroc']))} |")

    # ================================================================
    # 2. Revocations per run (B, C only)
    # ================================================================
    lines.append("\n## 2. Revocations per run\n")
    lines.append("| Run | Cheater revoked | Decoy revoked | Honest revoked | Total revoked |")
    lines.append("|-----|-----------------|---------------|----------------|---------------|")
    for cond in ["B", "C"]:
        for seed in SEED_RANGE:
            events = load_run(cond, seed)
            _, cheater_eids, honest_eids, decoy_eids = entry_info(events)
            ch_rev = dec_rev = hon_rev = 0
            for e in events:
                if e["type"] == "revocation":
                    eid = e["payload"]["entry_id"]
                    if eid in cheater_eids: ch_rev += 1
                    elif eid in decoy_eids: dec_rev += 1
                    elif eid in honest_eids: hon_rev += 1
            lines.append(f"| {cond}_seed{seed} | {ch_rev} | {dec_rev} | {hon_rev} | {ch_rev+dec_rev+hon_rev} |")

    # ================================================================
    # 3. C only: decoy flag rate by round band
    # ================================================================
    lines.append("\n## 3. Condition C: decoy flag rate by round band\n")
    bands = [(0, 6), (7, 13), (14, 19)]
    lines.append("| Run | R0–6 flags/reviews | R7–13 flags/reviews | R14–19 flags/reviews |")
    lines.append("|-----|--------------------|---------------------|----------------------|")

    agg_band = {b: {"flags": 0, "reviews": 0} for b in bands}
    for seed in SEED_RANGE:
        events = load_run("C", seed)
        _, _, _, decoy_eids = entry_info(events)
        band_data = {b: {"flags": 0, "reviews": 0} for b in bands}
        for e in events:
            if e["type"] == "review" and e["agent"] in HONEST:
                eid = e["payload"]["entry_id"]
                if eid not in decoy_eids:
                    continue
                rnd = e["round"]
                for lo, hi in bands:
                    if lo <= rnd <= hi:
                        band_data[(lo, hi)]["reviews"] += 1
                        agg_band[(lo, hi)]["reviews"] += 1
                        if e["payload"]["verdict"] == "exploit":
                            band_data[(lo, hi)]["flags"] += 1
                            agg_band[(lo, hi)]["flags"] += 1
                        break
        cells = []
        for b in bands:
            f = band_data[b]["flags"]
            r = band_data[b]["reviews"]
            rate = f"{f/r*100:.1f}%" if r > 0 else "N/A"
            cells.append(f"{rate} ({f}/{r})")
        lines.append(f"| C_seed{seed} | {cells[0]} | {cells[1]} | {cells[2]} |")

    lines.append("\n### Aggregate\n")
    cells = []
    for b in bands:
        f = agg_band[b]["flags"]
        r = agg_band[b]["reviews"]
        rate = f"{f/r*100:.1f}%" if r > 0 else "N/A"
        cells.append(f"{rate} ({f}/{r})")
    lines.append(f"| All C | {cells[0]} | {cells[1]} | {cells[2]} |")

    # ================================================================
    # 4. C only: average CA payment by verdict on decoy entries
    # ================================================================
    lines.append("\n## 4. Condition C: CA payments on decoy entry verdicts\n")

    exploit_payments = []
    legit_payments = []
    for seed in SEED_RANGE:
        events = load_run("C", seed)
        _, _, _, decoy_eids = entry_info(events)
        # Map reviews to their CA payments
        # CA payments log entry_id, so match by (agent, entry_id, round)
        # First collect all reviews on decoy entries
        decoy_reviews = []
        for e in events:
            if e["type"] == "review" and e["agent"] in HONEST:
                eid = e["payload"]["entry_id"]
                if eid in decoy_eids and e["payload"]["verdict"] in ("exploit", "legit"):
                    decoy_reviews.append({
                        "agent": e["agent"],
                        "entry_id": eid,
                        "verdict": e["payload"]["verdict"],
                        "round": e["round"],
                    })
        # Collect CA payments
        ca_by_agent_entry = {}
        for e in events:
            if e["type"] == "ca_payment":
                key = (e["agent"], e["payload"]["entry_id"])
                ca_by_agent_entry[key] = e["payload"].get("payment", e["payload"].get("score", 0) * 10)
        for rv in decoy_reviews:
            key = (rv["agent"], rv["entry_id"])
            if key in ca_by_agent_entry:
                pmt = ca_by_agent_entry[key]
                if rv["verdict"] == "exploit":
                    exploit_payments.append(pmt)
                else:
                    legit_payments.append(pmt)

    lines.append("| Verdict on decoy | Count | Mean CA payment | Median | Min | Max |")
    lines.append("|------------------|-------|-----------------|--------|-----|-----|")
    for label, payments in [("exploit", exploit_payments), ("legit", legit_payments)]:
        if payments:
            mean_p = sum(payments) / len(payments)
            sorted_p = sorted(payments)
            median_p = sorted_p[len(sorted_p)//2]
            lines.append(f"| {label} | {len(payments)} | {mean_p:.2f} | {median_p:.1f} | {min(payments):.1f} | {max(payments):.1f} |")
        else:
            lines.append(f"| {label} | 0 | N/A | N/A | N/A | N/A |")

    # ================================================================
    # 5. Herding: decoy flag rate with/without prior public accusation
    # ================================================================
    lines.append("\n## 5. Herding: decoy flag rate by prior public accusation visibility\n")
    lines.append("| Condition | Prior accusation | Exploit verdicts / reviews | Flag rate |")
    lines.append("|-----------|------------------|---------------------------|-----------|")

    for cond in CONDITIONS:
        saw_flags = saw_reviews = 0
        nosee_flags = nosee_reviews = 0
        for seed in SEED_RANGE:
            events = load_run(cond, seed)
            _, _, _, decoy_eids = entry_info(events)
            for e in events:
                if e["type"] == "review" and e["agent"] in HONEST:
                    eid = e["payload"]["entry_id"]
                    if eid not in decoy_eids:
                        continue
                    saw_prior = e["payload"].get("saw_prior_accusation", False)
                    if saw_prior:
                        saw_reviews += 1
                        if e["payload"]["verdict"] == "exploit":
                            saw_flags += 1
                    else:
                        nosee_reviews += 1
                        if e["payload"]["verdict"] == "exploit":
                            nosee_flags += 1
        saw_rate = saw_flags/saw_reviews if saw_reviews > 0 else None
        nosee_rate = nosee_flags/nosee_reviews if nosee_reviews > 0 else None
        lines.append(f"| {cond} | Yes | {saw_flags}/{saw_reviews} | {fmt(saw_rate, True)} |")
        lines.append(f"| {cond} | No | {nosee_flags}/{nosee_reviews} | {fmt(nosee_rate, True)} |")

    with open("analysis/exploratory.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote analysis/exploratory.md")


if __name__ == "__main__":
    main()
