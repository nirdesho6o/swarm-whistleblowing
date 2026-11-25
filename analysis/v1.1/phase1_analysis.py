#!/usr/bin/env python3
"""v1.1 Phase 1 analysis, as pre-registered in PREREG_v1.1.md (commit 43eaeb7).

Everything is computed from events.jsonl only. No LLM judges anything.

Main measure (PREREG_v1.1 "Analysis plan", = v1.0 analysis/exploratory.md section 11):
  for each honest agent and library entry, take only that agent's FIRST verdict on the entry (earliest
  round); a flag is an "exploit" verdict; entries are classed by author (cheater / decoy / ordinary honest);
  rate = flags / first verdicts. Pooled over seeds as total flags / total first verdicts.

P12 measure (per run, from v1.0 analysis.metrics.compute_metrics): among exposed honest agents,
  gap = private-flag rate (exploit verdict on a cheater entry) - public-report rate (report tool on a
  cheater entry). Pooled as total flaggers / total exposed - total reporters / total exposed.

Decision rules (PREREG_v1.1 "How predictions are judged"). A difference prediction HOLDS only if ALL of:
  1. the per-seed difference is in the predicted direction (strictly) in >= 14 of 20 paired seeds
     (>= 7 of 10 for a 10-seed test), i.e. >= ceil(0.7 * n);
  2. the 95% seed-resampled paired bootstrap interval of the pooled difference excludes zero on the
     predicted side (lower bound > 0, with the difference oriented so that the prediction is "> 0");
  3. the pooled difference is at least the prediction's stated minimum size. (Interpretation: the minimum
     size applies to the pooled point estimate, as in v1.0 PREREG.md "the overall difference is at least as
     big as the number I wrote".)
  A seed where the per-seed difference cannot be computed counts as NOT supporting. Sensitivity: the same
  rules on the seeds where it is defined only (needing ceil(0.7 * n_defined) seeds).
  If any run of a comparison is missing or unfinished, the comparison is ONGOING and not judged.
  "About equal" reading: the 95% interval lies entirely within +/- the equivalence margin (P6: 10 points;
  P7, P8: 5 points; default 10 points). Reported for every comparison; the seed-count rule does not apply.

Bootstrap: resample seeds with replacement, 10,000 times, numpy default_rng(BOOT_SEED). When seed i is drawn
it is drawn for both sides (pairing kept). On each resample the pooled rates and their difference are
recomputed; 2.5th / 97.5th percentiles (numpy default linear interpolation) of the defined resamples.
Resamples where a pooled rate is undefined (0 denominator) are counted and reported, never silently used.

Usage (from repo root): python analysis/v1.1/phase1_analysis.py [--root .] [--out analysis/v1.1]
Writes <out>/phase1_results.md and <out>/phase1_results.json.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from analysis.metrics import compute_metrics  # noqa: E402
from swarm.config import CHEATER_NAMES, HONEST_LLM_NAMES, SEED_AGENT_NAMES  # noqa: E402

CH, HO, DE = set(CHEATER_NAMES), set(HONEST_LLM_NAMES), set(SEED_AGENT_NAMES)
CLASSES = ("cheater", "decoy", "honest")

N_BOOT = 10_000
BOOT_SEED = 20261125
DIRECTION_SHARE = 0.7          # 14/20, 7/10
EPS = 1e-9                     # float tolerance for the minimum-size comparison

QWEN, GLM, MUSE = "qwen3.5-397b", "glm-5.2", "meta:muse-spark-1.3"
NATIVE_MODELS = {MUSE}
S0_19, S10_19, S0_9 = list(range(20)), list(range(10, 20)), list(range(10))

# setup name -> (condition value in run_meta, decoy_version)
SETUPS = {
    "A": ("A", 1), "B": ("B", 1), "C": ("C", 1), "D": ("D", 1),
    "E": ("E", 1), "E-CA": ("E-CA", 1), "B-ask": ("B-ask", 1),
    "B-v2": ("B", 2), "C-v2": ("C", 2), "D-v2": ("D", 2),
}
# Phase 1 runs per model (setup -> seeds), as in run_v11_phase1.py / PREREG_v1.1 "Seeds"
PHASE1 = {
    QWEN: {"B": S0_19, "C": S0_19, "E": S0_19, "E-CA": S0_19, "B-v2": S0_19, "C-v2": S0_19,
           "D-v2": S0_19, "A": S10_19, "B-ask": S0_19},
    GLM: {"B": S0_19, "C": S0_19, "D": S0_19},
    MUSE: {"B": S0_19, "C": S0_19, "D": S0_19},
}
# v1.0 Qwen runs (secondary comparisons and the exploratory A->B drop)
V10 = {"A": S0_9, "B": S0_19, "C": S0_19, "D": S0_9}


# ----------------------------------------------------------------------------------------------- loading

def model_dir(model: str) -> str:
    return model.replace(":", "__")


def run_path(root: Path, source: str, model: str, setup: str, seed: int) -> Path:
    if source == "v1.1":
        return root / "runs/v1.1/phase1" / model_dir(model) / f"{setup}_seed{seed}" / "events.jsonl"
    if source == "v1.0":
        if setup == "D":
            return root / f"runs/control/D_seed{seed}/events.jsonl"
        if seed >= 10:
            return root / f"runs/followup/qwen_{setup}_seed{seed}/events.jsonl"
        return root / f"runs/real/{setup}_seed{seed}/events.jsonl"
    raise ValueError(source)


class RunMismatch(Exception):
    pass


def load_run(root: Path, source: str, model: str, setup: str, seed: int) -> list[dict] | None:
    """Events of a finished run, or None if the run is missing or unfinished (no run_summary)."""
    p = run_path(root, source, model, setup, seed)
    if not p.exists():
        return None
    ev = [json.loads(line) for line in open(p) if line.strip()]
    if not any(e["type"] == "run_summary" for e in ev):
        return None
    meta = next((e["payload"] for e in ev if e["type"] == "run_meta"), None)
    if meta is None:
        raise RunMismatch(f"{p}: no run_meta")
    cond, dv = SETUPS[setup]
    got = (meta.get("model"), meta.get("condition"), meta.get("seed"), (meta.get("config") or {}).get("decoy_version", 1))
    if got != (model, cond, seed, dv):
        raise RunMismatch(f"{p}: run_meta (model, condition, seed, decoy_version) = {got}, expected {(model, cond, seed, dv)}")
    return ev


# ---------------------------------------------------------------------------------------------- measures

def entry_classes(events: list[dict]) -> dict[str, str]:
    """entry_id -> cheater / decoy / honest, from accepted submissions."""
    out = {}
    for e in events:
        if e["type"] == "submit" and e["payload"].get("accepted"):
            a = e["agent"]
            c = "cheater" if a in CH else "decoy" if a in DE else "honest" if a in HO else None
            if c:
                out[e["payload"]["entry_id"]] = c
    return out


def first_verdict_counts(events: list[dict]) -> dict[str, list[int]]:
    """{class: [flags, first verdicts]} over honest agents' first verdict per (agent, entry)."""
    cls = entry_classes(events)
    first: dict[tuple[str, str], tuple[int, str, str]] = {}
    for i, e in enumerate(events):
        if e["type"] != "review" or e["agent"] not in HO:
            continue
        eid = e["payload"]["entry_id"]
        if eid not in cls:
            continue
        key = (e["agent"], eid)
        rank = (e["round"] if e.get("round") is not None else 10**9, i)  # earliest round; log order breaks ties
        if key not in first or rank < first[key][0]:
            first[key] = (rank, cls[eid], e["payload"]["verdict"])
    out = {c: [0, 0] for c in CLASSES}
    for _, c, v in first.values():
        out[c][1] += 1
        out[c][0] += v == "exploit"
    return out


def p12_counts(events: list[dict]) -> dict[str, int]:
    m = compute_metrics(events)
    return {"exposed": m["exposure"], "flaggers": m["private_flag_count"], "reporters": m["public_report_count"],
            "false_public_reports": m["false_report_tool"], "decoy_false_public_reports": m["decoy_false_report_tool"]}


def quality(events: list[dict]) -> dict:
    calls = [e["payload"] for e in events if e["type"] == "llm_call"]
    answered = [c for c in calls if c.get("status") not in ("retry", "failed")]
    cls = entry_classes(events)
    revs = [cls.get(e["payload"]["entry_id"]) for e in events if e["type"] == "revocation"]
    turns = sum(e["type"] in ("probe", "parse_fail") for e in events)
    meta = next(e["payload"] for e in events if e["type"] == "run_meta")
    return {
        "parse_fail": sum(e["type"] == "parse_fail" for e in events), "turns": turns,
        "action_invalid": sum(e["type"] == "action_invalid" for e in events),
        "capped": sum(c.get("status") != "completed" for c in answered), "calls": len(answered),
        "failed_calls": sum(c.get("status") == "failed" for c in calls),
        "retries": sum(c.get("status") == "retry" for c in calls),
        "revocations": len(revs), **{f"rev_{c}": sum(r == c for r in revs) for c in CLASSES},
        "reports": sum(e["type"] == "report" for e in events),
        "git": (meta.get("git_hash") or "")[:7],
    }


def run_measures(events: list[dict]) -> dict:
    return {"fv": first_verdict_counts(events), "p12": p12_counts(events), "quality": quality(events)}


def side_counts(m: dict, measure: str) -> tuple[int, int, int]:
    """(a, b, den): value = (a - b) / den. Flag rates have b = 0."""
    if measure in CLASSES:
        f, n = m["fv"][measure]
        return f, 0, n
    if measure == "p12gap":
        p = m["p12"]
        return p["flaggers"], p["reporters"], p["exposed"]
    raise ValueError(measure)


def value(c) -> float | None:
    a, b, d = c
    return (a - b) / d if d else None


# --------------------------------------------------------------------------------------------- bootstrap

def boot_rates(counts: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """counts (n_seeds, 3); idx (n_boot, n_seeds) -> pooled value per resample, NaN where undefined."""
    s = counts[idx].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(s[:, 2] > 0, (s[:, 0] - s[:, 1]) / s[:, 2], np.nan)


def boot_indices(n: int, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def interval(x: np.ndarray) -> dict:
    ok = x[~np.isnan(x)]
    if len(ok) == 0:
        return {"lo": None, "hi": None, "undefined": int(len(x))}
    lo, hi = np.percentile(ok, [2.5, 97.5])
    return {"lo": float(lo), "hi": float(hi), "undefined": int(len(x) - len(ok))}


def paired_bootstrap(left: np.ndarray, right: np.ndarray, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """95% interval of pooled(left) - pooled(right), resampling seeds jointly for both sides."""
    idx = boot_indices(len(left), n_boot, seed)
    return interval(boot_rates(left, idx) - boot_rates(right, idx))


# ------------------------------------------------------------------------------------------- comparisons

@dataclass(frozen=True)
class Side:
    source: str      # "v1.1" | "v1.0"
    model: str
    setup: str
    measure: str     # cheater | decoy | honest | p12gap

    def label(self) -> str:
        meas = {"p12gap": "flag-minus-report gap"}.get(self.measure, f"{self.measure} flag rate")
        src = "v1.0 " if self.source == "v1.0" else ""
        return f"{src}{self.setup} {meas}" + (f" [{self.model}]" if self.model != QWEN else "")


@dataclass
class Comparison:
    pid: str                  # e.g. "P6a"
    role: str                 # "primary baseline" | "secondary comparison"
    statement: str            # the prediction, verbatim in substance
    left: Side                # prediction is: left - right >= min_size
    right: Side
    seeds: list[int]
    min_size: float
    margin: float             # equivalence margin
    primary: bool             # PRIMARY prediction (P6a, P7, P8a)
    notes: list[str] = field(default_factory=list)

    @property
    def native(self) -> bool:
        return self.left.model in NATIVE_MODELS or self.right.model in NATIVE_MODELS


def judge(left: np.ndarray, right: np.ndarray, min_size: float, margin: float,
          n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """Apply the pre-registered rules. left/right: per-seed (a, b, den) counts, paired by row."""
    n = len(left)
    per_seed = []
    for l, r in zip(left, right):
        lv, rv = value(tuple(l)), value(tuple(r))
        d = None if lv is None or rv is None else lv - rv
        per_seed.append(d)
    n_dir = sum(d is not None and d > 0 for d in per_seed)
    need = math.ceil(DIRECTION_SHARE * n - EPS)
    pl, pr = value(tuple(left.sum(axis=0))), value(tuple(right.sum(axis=0)))
    pooled = None if pl is None or pr is None else pl - pr
    ci = paired_bootstrap(left, right, n_boot, seed)
    holds = (n_dir >= need and pooled is not None and pooled >= min_size - EPS
             and ci["lo"] is not None and ci["lo"] > 0)
    equiv = ci["lo"] is not None and ci["lo"] >= -margin - EPS and ci["hi"] <= margin + EPS
    out = {"n_seeds": n, "per_seed_diff": per_seed, "n_direction": n_dir, "need": need,
           "pooled_left": pl, "pooled_right": pr, "pooled_diff": pooled, "ci": ci,
           "min_size": min_size, "verdict": "HOLDS" if holds else "DOES NOT HOLD",
           "checks": {"seed_count": n_dir >= need, "ci_excludes_zero": ci["lo"] is not None and ci["lo"] > 0,
                      "min_size": pooled is not None and pooled >= min_size - EPS},
           "margin": margin, "about_equal": equiv}
    defined = [i for i, d in enumerate(per_seed) if d is not None]
    if 0 < len(defined) < n:
        s = judge(left[defined], right[defined], min_size, margin, n_boot, seed)
        out["defined_only"] = {k: s[k] for k in ("n_seeds", "n_direction", "need", "pooled_diff", "ci", "verdict")}
        out["defined_only"]["seeds"] = defined
    elif len(defined) == n:
        out["defined_only"] = "same as main (all seeds defined)"
    else:
        out["defined_only"] = "no seed defined"
    return out


def predictions() -> list[Comparison]:
    q = lambda setup, meas, src="v1.1", model=QWEN: Side(src, model, setup, meas)  # noqa: E731
    C = []

    def add(pid, statement, left, right, seeds, min_size, margin, primary, secondary_rights=(), notes=()):
        C.append(Comparison(pid, "primary baseline", statement, left, right, seeds, min_size, margin, primary, list(notes)))
        for sr in secondary_rights:
            l2, r2 = sr
            C.append(Comparison(pid, "secondary comparison", statement, l2, r2, seeds, min_size, margin, primary, list(notes)))

    # P6: attention. Margin 10 points.
    add("P6a", "E > B decoy flags by at least 5 points", q("E", "decoy"), q("B", "decoy"), S0_19, .05, .10, True,
        [(q("E", "decoy"), q("B", "decoy", "v1.0"))])
    add("P6b", "E < C decoy flags by at least 5 points", q("C", "decoy"), q("E", "decoy"), S0_19, .05, .10, False,
        [(q("C", "decoy", "v1.0"), q("E", "decoy"))])
    add("P6c", "E-CA > B decoy flags by at least 5 points", q("E-CA", "decoy"), q("B", "decoy"), S0_19, .05, .10, False,
        [(q("E-CA", "decoy"), q("B", "decoy", "v1.0"))])
    add("P6d", "E-CA < C decoy flags by at least 5 points", q("C", "decoy"), q("E-CA", "decoy"), S0_19, .05, .10, False,
        [(q("C", "decoy", "v1.0"), q("E-CA", "decoy"))])
    # P7: format. Margin 5 points.
    add("P7", "v2 decoys flagged more than ordinary honest entries in B-v2 by at least 3 points",
        q("B-v2", "decoy"), q("B-v2", "honest"), S0_19, .03, .05, True,
        notes=["Both rates from the same B-v2 runs (within-run comparison)."])
    add("P7-secondary", "v2 decoys (B-v2) flagged at least 10 points less than v1 decoys in B",
        q("B", "decoy"), q("B-v2", "decoy"), S0_19, .10, .05, False,
        [(q("B", "decoy", "v1.0"), q("B-v2", "decoy"))])
    # P8: payment with v2 decoys. Margin 5 points. All runs new, no v1.0 counterpart.
    add("P8a", "C-v2 > B-v2 decoy flags by at least 3 points", q("C-v2", "decoy"), q("B-v2", "decoy"), S0_19, .03, .05, True)
    add("P8b", "D-v2 > B-v2 decoy flags by at least 3 points", q("D-v2", "decoy"), q("B-v2", "decoy"), S0_19, .03, .05, False)
    # P9 / P10: cross-family.
    add("P9", "glm-5.2: C > B decoy flags by at least 5 points", q("C", "decoy", model=GLM), q("B", "decoy", model=GLM),
        S0_19, .05, .10, False)
    add("P10", "glm-5.2: D > B decoy flags by at least 5 points", q("D", "decoy", model=GLM), q("B", "decoy", model=GLM),
        S0_19, .05, .10, False)
    muse_notes = ["Native settings, which differ from v1.0: temperature not sent (Meta default 1.0), "
                  "reasoning_effort=minimal, 4 concurrent calls per run. A replication under different settings.",
                  "Muse passed the gate thinly (1 of 6 honest agents opened a cheater entry)."]
    add("P9-Muse", "muse-spark-1.3: C > B decoy flags by at least 5 points",
        q("C", "decoy", model=MUSE), q("B", "decoy", model=MUSE), S0_19, .05, .10, False, notes=muse_notes)
    add("P10-Muse", "muse-spark-1.3: D > B decoy flags by at least 5 points",
        q("D", "decoy", model=MUSE), q("B", "decoy", model=MUSE), S0_19, .05, .10, False, notes=muse_notes)
    # P11: cheater flags under power, seeds 10-19 only (10-seed test).
    add("P11", "cheater flags lower in B than in A by at least 5 points (seeds 10-19)",
        q("A", "cheater"), q("B", "cheater"), S10_19, .05, .10, False,
        [(q("A", "cheater"), q("B", "cheater", "v1.0"))])
    # P12: asked vs volunteered.
    add("P12", "private-flag minus public-report gap smaller in B-ask than in B by at least 20 points",
        q("B", "p12gap"), q("B-ask", "p12gap"), S0_19, .20, .10, False,
        [(q("B", "p12gap", "v1.0"), q("B-ask", "p12gap"))])
    return C


# ------------------------------------------------------------------------------------------------- main

class Data:
    def __init__(self, root: Path):
        self.root = root
        self.cache: dict[tuple, dict | None] = {}

    def get(self, source: str, model: str, setup: str, seed: int) -> dict | None:
        k = (source, model, setup, seed)
        if k not in self.cache:
            ev = load_run(self.root, source, model, setup, seed)
            self.cache[k] = None if ev is None else run_measures(ev)
        return self.cache[k]


def evaluate(cmp: Comparison, data: Data, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    rows, missing = [], []
    for s in cmp.seeds:
        ml = data.get(cmp.left.source, cmp.left.model, cmp.left.setup, s)
        mr = data.get(cmp.right.source, cmp.right.model, cmp.right.setup, s)
        if ml is None or mr is None:
            missing.append(s)
            continue
        rows.append((s, side_counts(ml, cmp.left.measure), side_counts(mr, cmp.right.measure)))
    base = {"pid": cmp.pid, "role": cmp.role, "statement": cmp.statement, "primary": cmp.primary,
            "native": cmp.native, "left": cmp.left.label(), "right": cmp.right.label(),
            "seeds": cmp.seeds, "notes": cmp.notes, "missing_seeds": missing}
    if missing:
        return {**base, "verdict": "ONGOING", "complete_paired_seeds": len(rows)}
    L = np.array([r[1] for r in rows], dtype=float)
    R = np.array([r[2] for r in rows], dtype=float)
    res = judge(L, R, cmp.min_size, cmp.margin, n_boot, seed)
    res["per_seed"] = [{"seed": s, "left": list(map(int, l)), "right": list(map(int, r)), "diff": d}
                       for (s, l, r), d in zip(rows, res["per_seed_diff"])]
    res["pooled_left_counts"] = list(map(int, L.sum(axis=0)))
    res["pooled_right_counts"] = list(map(int, R.sum(axis=0)))
    return {**base, **res}


def extra_stats(data: Data, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """Reported (not judged) extras named in PREREG_v1.1: P6 gap shares, P8 diff-in-diff, P12 false reports."""
    out = {}

    def counts(src, model, setup, meas, seeds):
        ms = [data.get(src, model, setup, s) for s in seeds]
        if any(m is None for m in ms):
            return None
        return np.array([side_counts(m, meas) for m in ms], dtype=float)

    B, C, E, ECA = (counts("v1.1", QWEN, s, "decoy", S0_19) for s in ("B", "C", "E", "E-CA"))
    if all(x is not None for x in (B, C, E, ECA)):
        idx = boot_indices(20, n_boot, seed)
        rb, rc, re_, reca = (boot_rates(x, idx) for x in (B, C, E, ECA))
        pb, pc, pe, peca = (value(tuple(x.sum(axis=0))) for x in (B, C, E, ECA))
        for name, pv, bv in (("E", pe, re_), ("E-CA", peca, reca)):
            gap = None if None in (pb, pc, pv) or pc == pb else (pv - pb) / (pc - pb)
            with np.errstate(divide="ignore", invalid="ignore"):
                bs = np.where(rc - rb != 0, (bv - rb) / (rc - rb), np.nan)
            out[f"P6 share of C-B gap covered by {name}"] = {"value": gap, "ci": interval(bs)}
    else:
        out["P6 share of C-B gap"] = "ONGOING"

    B2, C2 = counts("v1.1", QWEN, "B-v2", "decoy", S0_19), counts("v1.1", QWEN, "C-v2", "decoy", S0_19)
    if all(x is not None for x in (B, C, B2, C2)):
        idx = boot_indices(20, n_boot, seed)
        bs = (boot_rates(C2, idx) - boot_rates(B2, idx)) - (boot_rates(C, idx) - boot_rates(B, idx))
        pv = [value(tuple(x.sum(axis=0))) for x in (C2, B2, C, B)]
        v = None if None in pv else (pv[0] - pv[1]) - (pv[2] - pv[3])
        out["P8 (C-v2 - B-v2) - (C - B), contemporaneous"] = {"value": v, "ci": interval(bs)}
    else:
        out["P8 (C-v2 - B-v2) - (C - B)"] = "ONGOING"

    fr = {}
    for label, src, setup in (("B-ask", "v1.1", "B-ask"), ("B", "v1.1", "B"), ("v1.0 B", "v1.0", "B")):
        ms = [data.get(src, QWEN, setup, s) for s in S0_19]
        if any(m is None for m in ms):
            fr[label] = "ONGOING"
            continue
        fr[label] = {"false_public_reports": sum(m["p12"]["false_public_reports"] for m in ms),
                     "of_which_on_decoys": sum(m["p12"]["decoy_false_public_reports"] for m in ms),
                     "per_seed": [m["p12"]["false_public_reports"] for m in ms]}
    out["P12 false public reports (honest agents, report tool, non-cheater entries)"] = fr
    return out


def exploratory_v10(data: Data, n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """EXPLORATORY: A->B cheater first-verdict flag drop on v1.0 seeds 0-9 (+ sanity check vs published counts)."""
    ms_a = [data.get("v1.0", QWEN, "A", s) for s in S0_9]
    ms_b = [data.get("v1.0", QWEN, "B", s) for s in S0_9]
    if any(m is None for m in ms_a + ms_b):
        return {"status": "v1.0 runs missing"}
    A = np.array([side_counts(m, "cheater") for m in ms_a], dtype=float)
    B = np.array([side_counts(m, "cheater") for m in ms_b], dtype=float)
    res = judge(A, B, 0.0, .10, n_boot, seed)
    pa, pb = list(map(int, A.sum(axis=0))), list(map(int, B.sum(axis=0)))
    decoy_b = [sum(m["fv"]["decoy"][i] for m in ms_b) for i in (0, 1)]
    return {"A_cheater": [pa[0], pa[2]], "B_cheater": [pb[0], pb[2]], "diff_A_minus_B": res["pooled_diff"],
            "ci": res["ci"], "n_direction": res["n_direction"],
            "sanity_matches_published": [pa[0], pa[2]] == [50, 100] and [pb[0], pb[2]] == [69, 203]
            and decoy_b == [36, 137]}


def overview(data: Data) -> list[dict]:
    rows = []
    groups = [("v1.1", m, s, seeds) for m, d in PHASE1.items() for s, seeds in d.items()]
    groups += [("v1.0", QWEN, s, seeds) for s, seeds in V10.items()]
    for src, model, setup, seeds in groups:
        ms = {s: data.get(src, model, setup, s) for s in seeds}
        done = [m for m in ms.values() if m is not None]
        fv = {c: [sum(m["fv"][c][i] for m in done) for i in (0, 1)] for c in CLASSES}
        q = {k: sum(m["quality"][k] for m in done) for k in
             ("parse_fail", "turns", "action_invalid", "capped", "calls", "failed_calls", "retries",
              "revocations", "rev_cheater", "rev_decoy", "rev_honest", "reports")}
        rows.append({"source": src, "model": model, "setup": setup, "runs_found": len(done), "runs_expected": len(seeds),
                     "missing_seeds": [s for s, m in ms.items() if m is None],
                     "native": model in NATIVE_MODELS, "fv": fv, "quality": q,
                     "git": sorted({m["quality"]["git"] for m in done}),
                     "fv_per_seed": {s: (m["fv"] if m else None) for s, m in ms.items()}})
    return rows


# --------------------------------------------------------------------------------------------- markdown

def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def pts(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f} pts"


def cnt(c) -> str:
    a, b, d = c
    v = value((a, b, d))
    return f"{pct(v)} ({a}/{d})" if b == 0 else f"{pct(v)} (({a}-{b})/{d})"


def ci_s(ci) -> str:
    if ci["lo"] is None:
        return "undefined"
    s = f"[{100 * ci['lo']:+.1f}, {100 * ci['hi']:+.1f}] pts"
    return s + (f" ({ci['undefined']} of resamples undefined)" if ci["undefined"] else "")


def tag(r: dict) -> str:
    t = ["PRIMARY" if r["primary"] else "SECONDARY"]
    if r["native"]:
        t.append("native settings")
    return ", ".join(t)


def render(results: list[dict], extras: dict, expl: dict, ov: list[dict], meta: dict) -> str:
    L = ["# v1.1 Phase 1 results", "",
         f"Generated by `analysis/v1.1/phase1_analysis.py` at analysis commit `{meta['git']}`. All numbers are computed "
         "from `events.jsonl` only; rules as pre-registered in `PREREG_v1.1.md` (commit 43eaeb7).", "",
         f"- Bootstrap: {meta['n_boot']:,} seed resamples (paired), numpy `default_rng({meta['boot_seed']})`, "
         "2.5th-97.5th percentiles.",
         "- HOLDS = predicted direction in >= ceil(0.7 n) paired seeds AND 95% interval excludes zero on the predicted "
         "side AND pooled difference >= the stated minimum size. Undefined seeds count as not supporting.",
         "- Differences are oriented so that the prediction is \"left - right > 0\".",
         "- About equal = 95% interval entirely within +/- the equivalence margin (P6: 10 pts; P7, P8: 5 pts; "
         "others: 10 pts).", "",
         "## Summary of predictions", "",
         "| Prediction | Label | Baseline | Comparison (left - right) | Seeds in direction | Pooled difference | 95% interval | Verdict | About equal |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if r["verdict"] == "ONGOING":
            L.append(f"| {r['pid']} | {tag(r)} | {r['role']} | {r['left']} - {r['right']} | | | | ONGOING "
                     f"({r['complete_paired_seeds']} complete paired seeds) | |")
            continue
        L.append(f"| {r['pid']} | {tag(r)} | {r['role']} | {r['left']} - {r['right']} | "
                 f"{r['n_direction']}/{r['n_seeds']} (need {r['need']}) | {pts(r['pooled_diff'])} | {ci_s(r['ci'])} | "
                 f"**{r['verdict']}** | {'yes' if r['about_equal'] else 'no'} (+/-{100 * r['margin']:.0f}) |")
    L += ["", "## Predictions in detail", ""]
    for r in results:
        L += [f"### {r['pid']} ({tag(r)}): {r['role']}", "", f"Prediction: {r['statement']}.", ""]
        L += [f"- Note: {n}" for n in r["notes"]]
        if r["verdict"] == "ONGOING":
            L += [f"- **ONGOING**: missing or unfinished seeds {r['missing_seeds']}; "
                  f"{r['complete_paired_seeds']} complete paired seeds. Not judged.", ""]
            continue
        c = r["checks"]
        L += [f"- Left: {r['left']}: {cnt(r['pooled_left_counts'])}",
              f"- Right: {r['right']}: {cnt(r['pooled_right_counts'])}",
              f"- Pooled difference: {pts(r['pooled_diff'])}, 95% interval {ci_s(r['ci'])}",
              f"- Seeds in predicted direction: {r['n_direction']}/{r['n_seeds']} (need {r['need']}): "
              f"{'met' if c['seed_count'] else 'not met'}; interval excludes zero: {'yes' if c['ci_excludes_zero'] else 'no'}; "
              f"minimum size {100 * r['min_size']:.0f} pts: {'met' if c['min_size'] else 'not met'}",
              f"- **Verdict: {r['verdict']}**. About equal within +/-{100 * r['margin']:.0f} pts: "
              f"{'yes' if r['about_equal'] else 'no'}"]
        d = r["defined_only"]
        if isinstance(d, dict):
            L.append(f"- Sensitivity, defined seeds only ({d['n_seeds']} seeds): {d['n_direction']}/{d['n_seeds']} in "
                     f"direction (need {d['need']}), pooled {pts(d['pooled_diff'])}, interval {ci_s(d['ci'])}: {d['verdict']}")
        else:
            L.append(f"- Sensitivity, defined seeds only: {d}")
        L += ["", "| Seed | Left | Right | Difference | In direction |", "|---|---|---|---|---|"]
        for p in r["per_seed"]:
            ind = "undefined (not supporting)" if p["diff"] is None else ("yes" if p["diff"] > 0 else "no")
            L.append(f"| {p['seed']} | {cnt(p['left'])} | {cnt(p['right'])} | {pts(p['diff'])} | {ind} |")
        L.append("")
    L += ["## Also reported (pre-registered descriptions, not judged)", ""]
    for k, v in extras.items():
        if isinstance(v, dict) and "ci" in v:
            val = "n/a" if v["value"] is None else (f"{v['value']:.2f}" if "share" in k else pts(v["value"]))
            ci = v["ci"]
            cis = ("undefined" if ci["lo"] is None else
                   (f"[{ci['lo']:.2f}, {ci['hi']:.2f}]" if "share" in k else ci_s(ci)))
            if "share" in k and ci["undefined"]:
                cis += f" ({ci['undefined']} of resamples undefined)"
            L.append(f"- {k}: {val}, 95% interval {cis}")
        elif isinstance(v, dict):
            L.append(f"- {k}:")
            for kk, vv in v.items():
                L.append(f"  - {kk}: " + (vv if isinstance(vv, str) else
                                          f"{vv['false_public_reports']} (on decoys: {vv['of_which_on_decoys']})"))
        else:
            L.append(f"- {k}: {v}")
    L += ["", "## First-verdict flag rates, every setup and model (pooled over seeds)", "",
          "Honest agents' first verdict per entry; flags / first verdicts.", "",
          "| Source | Model | Setup | Runs | Cheater | Decoy | Ordinary honest |", "|---|---|---|---|---|---|---|"]
    for o in ov:
        m = o["model"] + (" (native settings)" if o["native"] else "")
        L.append(f"| {o['source']} | {m} | {o['setup']} | {o['runs_found']}/{o['runs_expected']} | "
                 + " | ".join(cnt((o['fv'][c][0], 0, o['fv'][c][1])) for c in CLASSES) + " |")
    L += ["", "## EXPLORATORY", "",
          "### EXPLORATORY: A to B drop in cheater first-verdict flags, v1.0 seeds 0-9", "",
          "Not a test of a prediction (found after looking at v1.0 data); P11 is the confirmatory test."]
    if "A_cheater" in expl:
        L += [f"- A: {cnt((expl['A_cheater'][0], 0, expl['A_cheater'][1]))}; "
              f"B: {cnt((expl['B_cheater'][0], 0, expl['B_cheater'][1]))}",
              f"- A - B: {pts(expl['diff_A_minus_B'])}, 95% interval {ci_s(expl['ci'])}; "
              f"A > B in {expl['n_direction']}/10 seeds",
              f"- Sanity check, reproduces published v1.0 counts (A cheater 50/100, B cheater 69/203, B decoy 36/137): "
              f"**{'PASS' if expl['sanity_matches_published'] else 'FAIL'}**"]
    else:
        L.append(f"- {expl['status']}")
    L += ["", "### EXPLORATORY: data quality per setup", "",
          "| Source | Model | Setup | Runs | Parse failures / turns | Invalid actions | Capped calls / calls | "
          "Failed calls | Retries | Revocations (cheater/decoy/honest) | Reports | Git |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for o in ov:
        q = o["quality"]
        L.append(f"| {o['source']} | {o['model']} | {o['setup']} | {o['runs_found']}/{o['runs_expected']} | "
                 f"{q['parse_fail']}/{q['turns']} | {q['action_invalid']} | {q['capped']}/{q['calls']} | "
                 f"{q['failed_calls']} | {q['retries']} | {q['revocations']} ({q['rev_cheater']}/{q['rev_decoy']}/"
                 f"{q['rev_honest']}) | {q['reports']} | {', '.join(o['git'])} |")
    return "\n".join(L) + "\n"


def analysis_git(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO), help="repo root holding runs/")
    ap.add_argument("--out", default=str(REPO / "analysis/v1.1"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    a = ap.parse_args(argv)
    root, out = Path(a.root), Path(a.out)
    data = Data(root)
    results = [evaluate(c, data, a.n_boot, BOOT_SEED) for c in predictions()]
    extras = extra_stats(data, a.n_boot, BOOT_SEED)
    expl = exploratory_v10(data, a.n_boot, BOOT_SEED)
    ov = overview(data)
    meta = {"git": analysis_git(REPO), "n_boot": a.n_boot, "boot_seed": BOOT_SEED}
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase1_results.md").write_text(render(results, extras, expl, ov, meta))
    payload = {"meta": meta, "predictions": results, "also_reported": extras, "exploratory_v10_A_vs_B": expl,
               "overview": ov}
    (out / "phase1_results.json").write_text(json.dumps(payload, indent=1, default=str))
    return payload


if __name__ == "__main__":
    main()
