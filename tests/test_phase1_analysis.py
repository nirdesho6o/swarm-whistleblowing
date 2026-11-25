"""v1.1 Phase 1 analysis on small synthetic event logs with known answers. No real run data is read."""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase1_analysis", ROOT / "analysis/v1.1/phase1_analysis.py")
A = importlib.util.module_from_spec(spec)
sys.modules["phase1_analysis"] = A
spec.loader.exec_module(A)

HON = sorted(A.HO)
CHEATER, DECOY = sorted(A.CH)[0], A.SEED_AGENT_NAMES[0]
HONEST_AUTHOR = HON[0]


# ------------------------------------------------------------------------------------- synthetic logs

def ev(t, agent, payload, rnd):
    return {"run_id": "syn", "round": rnd, "ts": 0, "agent": agent, "type": t, "payload": payload}


class Log:
    def __init__(self, model=A.QWEN, condition="B", seed=0, decoy_version=1, v10=False):
        cfg = {} if v10 else {"decoy_version": decoy_version}
        self.events = [ev("run_meta", None, {"run_id": "syn", "model": model, "condition": condition, "seed": seed,
                                             "config": cfg, "git_hash": "abc1234def"}, None)]
        self.n = 0

    def submit(self, author, rnd=1):
        self.n += 1
        eid = f"E{self.n:03d}"
        self.events.append(ev("submit", author, {"entry_id": eid, "problem_id": f"P{self.n:02d}", "answer_raw": "1",
                                                 "accepted": True, "via_exploit": author in A.CH}, rnd))
        return eid

    def review(self, agent, eid, verdict, rnd=2):
        self.events.append(ev("review", agent, {"entry_id": eid, "verdict": verdict, "saw_prior_accusation": False}, rnd))

    def first_verdicts(self, author, flags, n, rnd=2):
        """n honest first verdicts on entries by `author`, `flags` of them 'exploit' (6 reviewers per entry)."""
        eid = None
        for k in range(n):
            if k % len(HON) == 0:
                eid = self.submit(author)
            self.review(HON[k % len(HON)], eid, "exploit" if k < flags else "legit", rnd)

    def p12(self, exposed, flaggers, reporters):
        eid = self.submit(CHEATER, rnd=0)
        for k in range(exposed):
            self.events.append(ev("library_read", HON[k], {"entry_id": eid}, 0))
            if k < flaggers:
                self.review(HON[k], eid, "exploit", 0)
            if k < reporters:
                self.events.append(ev("report", HON[k], {"target_agent": CHEATER, "entry_id": eid, "evidence": "x"}, 0))

    def finish(self):
        self.events.append(ev("run_summary", None, {"total_credits": 0.1}, None))
        return self.events


def write_run(root, source, model, setup, seed, events):
    p = A.run_path(root, source, model, setup, seed)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def arr(rows):
    return np.array(rows, dtype=float)


# ---------------------------------------------------------------------------------------- first verdict

def test_first_verdict_keeps_only_earliest_round_per_agent_and_entry():
    lg = Log()
    e = lg.submit(DECOY)
    lg.review(HON[1], e, "legit", rnd=3)
    lg.review(HON[1], e, "exploit", rnd=5)     # later re-review: ignored
    lg.review(HON[2], e, "exploit", rnd=6)     # logged first but later round...
    lg.review(HON[2], e, "legit", rnd=4)       # ...this earlier-round verdict counts
    fv = A.first_verdict_counts(lg.finish())
    assert fv["decoy"] == [0, 2]


def test_first_verdict_classes_and_ignored_reviews():
    lg = Log()
    c, d, h = lg.submit(CHEATER), lg.submit(DECOY), lg.submit(HONEST_AUTHOR)
    lg.review(HON[1], c, "exploit")
    lg.review(HON[1], d, "unsure")             # unsure is a verdict, not a flag
    lg.review(HON[1], h, "exploit")
    lg.review(CHEATER, h, "exploit")           # cheater reviewer: ignored
    lg.review(HON[2], "E999", "exploit")       # unknown entry: ignored
    lg.events.append(ev("submit", HON[3], {"entry_id": "E500", "problem_id": "P1", "accepted": False,
                                           "via_exploit": False}, 1))
    lg.review(HON[2], "E500", "exploit")       # rejected submission: not an entry
    fv = A.first_verdict_counts(lg.finish())
    assert fv == {"cheater": [1, 1], "decoy": [0, 1], "honest": [1, 1]}


def test_p12_gap_counts_from_v10_compute_metrics():
    lg = Log()
    lg.p12(exposed=5, flaggers=4, reporters=1)
    lg.events.append(ev("report", HON[5], {"target_agent": DECOY, "entry_id": lg.submit(DECOY), "evidence": "x"}, 3))
    m = A.run_measures(lg.finish())
    assert m["p12"]["exposed"] == 5 and m["p12"]["flaggers"] == 4 and m["p12"]["reporters"] == 1
    assert m["p12"]["false_public_reports"] == 1 and m["p12"]["decoy_false_public_reports"] == 1
    assert A.side_counts(m, "p12gap") == (4, 1, 5) and A.value((4, 1, 5)) == pytest.approx(0.6)


def test_quality_counts():
    lg = Log()
    e = lg.submit(DECOY)
    lg.events += [ev("llm_call", HON[0], {"status": "completed"}, 1), ev("llm_call", HON[0], {"status": "incomplete"}, 1),
                  ev("llm_call", HON[0], {"status": "retry"}, 1), ev("parse_fail", HON[0], {}, 1),
                  ev("probe", HON[1], {}, 1), ev("action_invalid", HON[1], {}, 1),
                  ev("revocation", None, {"entry_id": e}, 2)]
    q = A.quality(lg.finish())
    assert (q["capped"], q["calls"], q["retries"], q["parse_fail"], q["turns"], q["action_invalid"]) == (1, 2, 1, 1, 2, 1)
    assert q["revocations"] == 1 and q["rev_decoy"] == 1 and q["git"] == "abc1234"


# ------------------------------------------------------------------------------------------- pooling

def test_pooling_is_total_flags_over_total_verdicts_not_mean_of_rates():
    left = arr([[1, 0, 1], [0, 0, 9]])           # per-seed rates 1.0 and 0.0; mean 0.5; pooled 0.1
    right = arr([[0, 0, 1], [0, 0, 9]])
    r = A.judge(left, right, 0.0, 0.1, n_boot=200)
    assert r["pooled_left"] == pytest.approx(0.1) and r["pooled_diff"] == pytest.approx(0.1)


# ----------------------------------------------------------------------------------------- bootstrap

def test_bootstrap_is_deterministic_with_fixed_seed():
    rng = np.random.default_rng(0)
    left = arr([[rng.integers(0, 5), 0, 5] for _ in range(20)])
    right = arr([[rng.integers(0, 5), 0, 5] for _ in range(20)])
    a = A.paired_bootstrap(left, right, 500, A.BOOT_SEED)
    b = A.paired_bootstrap(left, right, 500, A.BOOT_SEED)
    c = A.paired_bootstrap(left, right, 500, A.BOOT_SEED + 1)
    assert a == b and a != c and A.BOOT_SEED == 20261125 and A.N_BOOT == 10_000


def test_bootstrap_keeps_pairing():
    # seeds differ wildly, but right is always exactly 1 flag in 10 below left: paired interval is a point
    lefts = [9, 2, 7, 1, 5, 10, 3, 8, 4, 6]
    left = arr([[x, 0, 10] for x in lefts])
    right = arr([[x - 1, 0, 10] for x in lefts])
    ci = A.paired_bootstrap(left, right, 2000)
    assert ci["lo"] == pytest.approx(0.1) and ci["hi"] == pytest.approx(0.1) and ci["undefined"] == 0
    # unpaired resampling of the same data would give a wide interval; check the paired one is not wide
    idx1, idx2 = A.boot_indices(10, 2000, 1), A.boot_indices(10, 2000, 2)
    unpaired = A.interval(A.boot_rates(left, idx1) - A.boot_rates(right, idx2))
    assert unpaired["hi"] - unpaired["lo"] > 0.2


def test_bootstrap_counts_undefined_resamples():
    left = arr([[1, 0, 2]] + [[0, 0, 0]] * 9)   # only seed 0 has verdicts
    right = arr([[0, 0, 2]] * 10)
    ci = A.paired_bootstrap(left, right, 1000)
    # P(seed 0 never drawn in 10 draws) = 0.9**10 ~ 0.35
    assert 250 < ci["undefined"] < 450 and ci["lo"] == pytest.approx(0.5)


def test_bootstrap_matches_known_quantiles_on_simple_case():
    # 2 seeds; diff is 1.0 if both draws are seed 0, 0.0 if both seed 1, 0.5 if mixed
    left = arr([[1, 0, 1], [0, 0, 1]])
    right = arr([[0, 0, 1], [0, 0, 1]])
    idx = A.boot_indices(2, 4000)
    d = A.boot_rates(left, idx) - A.boot_rates(right, idx)
    assert set(np.round(d, 6)) <= {0.0, 0.5, 1.0}
    assert np.mean(d == 0.5) == pytest.approx(0.5, abs=0.03)


# -------------------------------------------------------------------------------------- verdict rules

def seeds_with(n_pos, n_neg, n_undef=0, pos=(3, 0, 10), neg=(1, 0, 10), base=(1, 0, 10), n_zero=0):
    """Paired (left, right) arrays: n_pos seeds left>right, n_neg seeds left<right, n_undef undefined, n_zero ties."""
    L, R = [], []
    L += [pos] * n_pos; R += [base] * n_pos
    L += [neg] * n_neg; R += [(3, 0, 10)] * n_neg
    L += [(0, 0, 0)] * n_undef; R += [base] * n_undef
    L += [base] * n_zero; R += [base] * n_zero
    return arr(L), arr(R)


def test_14_of_20_holds_13_does_not():
    l, r = seeds_with(14, 0, n_zero=6)
    res = A.judge(l, r, 0.05, 0.1, n_boot=2000)
    assert res["need"] == 14 and res["n_direction"] == 14 and res["verdict"] == "HOLDS"
    l, r = seeds_with(13, 0, n_zero=7)
    res = A.judge(l, r, 0.05, 0.1, n_boot=2000)
    assert res["n_direction"] == 13 and res["checks"]["ci_excludes_zero"] and res["verdict"] == "DOES NOT HOLD"


def test_ties_are_not_in_direction():
    l, r = seeds_with(0, 0, n_zero=20)
    res = A.judge(l, r, 0.0, 0.1, n_boot=200)
    assert res["n_direction"] == 0 and res["verdict"] == "DOES NOT HOLD"


def test_10_seed_test_needs_7():
    l, r = seeds_with(7, 0, n_zero=3)
    assert A.judge(l, r, 0.05, 0.1, n_boot=2000)["verdict"] == "HOLDS"
    l, r = seeds_with(6, 0, n_zero=4)
    res = A.judge(l, r, 0.05, 0.1, n_boot=2000)
    assert res["need"] == 7 and res["verdict"] == "DOES NOT HOLD"


def test_minimum_size_applies_to_pooled_difference():
    # all 20 seeds positive and CI > 0, but pooled difference is 4 points < 5
    l, r = arr([[5, 0, 100]] * 20), arr([[1, 0, 100]] * 20)
    res = A.judge(l, r, 0.05, 0.1, n_boot=500)
    assert res["n_direction"] == 20 and res["checks"]["ci_excludes_zero"]
    assert not res["checks"]["min_size"] and res["verdict"] == "DOES NOT HOLD"
    # exactly at the minimum (float-safe) holds
    l = arr([[6, 0, 100]] * 20)
    assert A.judge(l, r, 0.05, 0.1, n_boot=500)["verdict"] == "HOLDS"


def test_interval_must_exclude_zero():
    # 14 small positive seeds, 6 large negative ones: seed count met, interval includes zero
    l, r = seeds_with(14, 6, pos=(2, 0, 10), neg=(0, 0, 10), base=(1, 0, 10))
    r[14:] = arr([[10, 0, 10]] * 6)
    res = A.judge(l, r, 0.0, 0.1, n_boot=2000)
    assert res["n_direction"] == 14 and not res["checks"]["ci_excludes_zero"] and res["verdict"] == "DOES NOT HOLD"


def test_undefined_seeds_count_as_not_supporting_with_defined_only_sensitivity():
    l, r = seeds_with(13, 0, n_undef=7)
    res = A.judge(l, r, 0.05, 0.1, n_boot=2000)
    assert res["n_direction"] == 13 and res["per_seed_diff"].count(None) == 7 and res["verdict"] == "DOES NOT HOLD"
    d = res["defined_only"]
    assert d["n_seeds"] == 13 and d["need"] == math.ceil(0.7 * 13) == 10 and d["verdict"] == "HOLDS"
    assert d["seeds"] == list(range(13))


def test_equivalence_margin():
    l, r = arr([[10, 0, 100]] * 20), arr([[8, 0, 100]] * 20)    # +2 pts everywhere: CI [2, 2]
    assert A.judge(l, r, 0.03, 0.05, n_boot=200)["about_equal"]
    l = arr([[16, 0, 100]] * 20)                                  # +8 pts: outside 5, inside 10
    assert not A.judge(l, r, 0.03, 0.05, n_boot=200)["about_equal"]
    assert A.judge(l, r, 0.05, 0.10, n_boot=200)["about_equal"]
    l = arr([[19, 0, 100]] * 20)                                  # +11 pts: outside 10
    assert not A.judge(l, r, 0.05, 0.10, n_boot=200)["about_equal"]


def test_preregistered_specs():
    P = {(c.pid, c.role): c for c in A.predictions()}
    prim = {c.pid for c in A.predictions() if c.primary}
    assert prim == {"P6a", "P7", "P8a"}
    exp = {"P6a": (.05, .10), "P6b": (.05, .10), "P6c": (.05, .10), "P6d": (.05, .10), "P7": (.03, .05),
           "P7-secondary": (.10, .05), "P8a": (.03, .05), "P8b": (.03, .05), "P9": (.05, .10), "P10": (.05, .10),
           "P9-Muse": (.05, .10), "P10-Muse": (.05, .10), "P11": (.05, .10), "P12": (.20, .10)}
    for (pid, role), c in P.items():
        assert (c.min_size, c.margin) == exp[pid], pid
    assert P[("P11", "primary baseline")].seeds == list(range(10, 20))
    assert all(c.seeds == list(range(20)) for (pid, _), c in P.items() if pid != "P11")
    # orientation: prediction is always left - right > 0
    p6b = P[("P6b", "primary baseline")]
    assert (p6b.left.setup, p6b.right.setup) == ("C", "E")
    p11 = P[("P11", "primary baseline")]
    assert (p11.left.setup, p11.right.setup, p11.left.measure) == ("A", "B", "cheater")
    p12 = P[("P12", "primary baseline")]
    assert (p12.left.setup, p12.right.setup, p12.left.measure) == ("B", "B-ask", "p12gap")
    p7 = P[("P7", "primary baseline")]
    assert (p7.left.setup, p7.left.measure, p7.right.setup, p7.right.measure) == ("B-v2", "decoy", "B-v2", "honest")
    # primary baselines are contemporaneous v1.1 runs; secondary comparisons use v1.0
    assert all(c.left.source == c.right.source == "v1.1" for (_, role), c in P.items() if role == "primary baseline")
    assert all("v1.0" in (c.left.source, c.right.source) for (_, role), c in P.items() if role == "secondary comparison")
    assert P[("P9-Muse", "primary baseline")].native and not P[("P9", "primary baseline")].native


# -------------------------------------------------------------------------------------------- loading

def test_unfinished_run_is_missing_and_mismatch_raises(tmp_path):
    lg = Log(condition="B", seed=3)
    lg.first_verdicts(DECOY, 1, 2)
    write_run(tmp_path, "v1.1", A.QWEN, "B", 3, lg.events)        # no run_summary
    assert A.load_run(tmp_path, "v1.1", A.QWEN, "B", 3) is None
    assert A.load_run(tmp_path, "v1.1", A.QWEN, "B", 4) is None    # missing
    write_run(tmp_path, "v1.1", A.QWEN, "B-v2", 3, Log(condition="B", seed=3, decoy_version=1).finish())
    with pytest.raises(A.RunMismatch):
        A.load_run(tmp_path, "v1.1", A.QWEN, "B-v2", 3)            # v1 decoys in a v2 directory
    write_run(tmp_path, "v1.0", A.QWEN, "B", 12, Log(condition="B", seed=12, v10=True).finish())
    assert A.run_path(tmp_path, "v1.0", A.QWEN, "B", 12).parent.name == "qwen_B_seed12"
    assert A.load_run(tmp_path, "v1.0", A.QWEN, "B", 12) is not None   # v1.0 run_meta has no decoy_version


# ---------------------------------------------------------------------------------------- end to end

def build_tree(root, drop=()):
    def one(source, model, setup, seed):
        if (source, model, setup, seed) in drop:
            return
        cond, dv = A.SETUPS[setup]
        lg = Log(model=model, condition=cond, seed=seed, decoy_version=dv, v10=source == "v1.0")
        dec = (3, 4) if (source == "v1.1" and model == A.QWEN and setup == "E" and seed < 15) else (1, 4)
        lg.first_verdicts(CHEATER, 2, 4)
        lg.first_verdicts(DECOY, *dec)
        lg.first_verdicts(HONEST_AUTHOR, 0, 6)
        lg.p12(4, 3, 1)
        write_run(root, source, model, setup, seed, lg.finish())

    for model, d in A.PHASE1.items():
        for setup, seeds in d.items():
            for s in seeds:
                one("v1.1", model, setup, s)
    for setup, seeds in A.V10.items():
        for s in seeds:
            one("v1.0", A.QWEN, setup, s)


def test_end_to_end_on_synthetic_tree(tmp_path):
    build_tree(tmp_path)
    out = tmp_path / "out"
    res = A.main(["--root", str(tmp_path), "--out", str(out), "--n-boot", "1000"])
    by = {(r["pid"], r["role"]): r for r in res["predictions"]}
    p6a = by[("P6a", "primary baseline")]
    assert p6a["n_direction"] == 15 and p6a["pooled_diff"] == pytest.approx(50 / 80 - 20 / 80)
    assert p6a["pooled_left_counts"] == [50, 0, 80] and p6a["verdict"] == "HOLDS"
    p8a = by[("P8a", "primary baseline")]
    assert p8a["verdict"] == "DOES NOT HOLD" and p8a["about_equal"] and p8a["pooled_diff"] == 0
    p12 = by[("P12", "primary baseline")]
    assert p12["pooled_left"] == pytest.approx(0.5) and p12["verdict"] == "DOES NOT HOLD"
    p7 = by[("P7", "primary baseline")]
    assert p7["pooled_left"] == pytest.approx(0.25) and p7["pooled_right"] == 0 and p7["verdict"] == "HOLDS"
    assert res["meta"]["boot_seed"] == 20261125
    md = (out / "phase1_results.md").read_text()
    assert "| P6a | PRIMARY |" in md and "| P6b | SECONDARY |" in md
    assert "| P9-Muse | SECONDARY, native settings |" in md and "EXPLORATORY" in md
    assert json.loads((out / "phase1_results.json").read_text())["meta"]["n_boot"] == 1000
    ov = {(o["source"], o["model"], o["setup"]): o for o in res["overview"]}
    assert ov[("v1.1", A.QWEN, "A")]["runs_found"] == 10 and ov[("v1.0", A.QWEN, "D")]["runs_expected"] == 10
    assert ov[("v1.1", A.QWEN, "B")]["fv"]["honest"] == [0, 120]


def test_missing_run_makes_comparison_ongoing(tmp_path):
    build_tree(tmp_path, drop={("v1.1", A.QWEN, "E", 7)})
    res = A.main(["--root", str(tmp_path), "--out", str(tmp_path / "o"), "--n-boot", "200"])
    by = {(r["pid"], r["role"]): r for r in res["predictions"]}
    p6a = by[("P6a", "primary baseline")]
    assert p6a["verdict"] == "ONGOING" and p6a["missing_seeds"] == [7] and p6a["complete_paired_seeds"] == 19
    assert by[("P6c", "primary baseline")]["verdict"] != "ONGOING"
