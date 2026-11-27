"""Supplementary independent checks (written after step 4, to resolve specific comparison points).

Uses only verify/v1.2_phase15_check.py (this session's own code) and raw events.jsonl.
  1. formal reports de-duplicated by (honest agent, entry), all 7 cells; revocations incl. glm
  2. capped-call counts (status == "incomplete") with exact numerator/denominator
  3. EXPLORATORY §1: first submissions vs resubmissions, odd - stealthy, paired bootstrap + seed counts
  4. EXPLORATORY §5: v1.0 recognition split by what exposed honest agents opened, under the original
     content rule (int(x, 0): "=!01" -> bare) and the fixed rule ("=!01" on P09 -> correct number)
"""
import glob
import importlib.util
import json
import os
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("chk", os.path.join(HERE, "v1.2_phase15_check.py"))
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)

runs = chk.load_cells()
rng = np.random.default_rng(chk.BOOT_SEED + 1)

print("== 1. formal reports (unique honest agent, entry) and revocations ==")
for (m, cells) in (("qwen3.5-397b", chk.QWEN_CELLS), ("glm-5.2", chk.GLM_CELLS)):
    for c in cells:
        rep, rev, rep_all = Counter(), Counter(), Counter()
        for s in chk.SEEDS:
            r = runs[(m, c, s)]
            seen = set()
            for rnd, a, p in r["reports"]:
                en = r["entries"].get(p.get("entry_id"))
                cls = en["cls"] if en else "no_entry"
                rep_all[cls] += 1
                if chk.honest(a) and (a, p.get("entry_id")) not in seen:
                    seen.add((a, p.get("entry_id")))
                    rep[cls] += 1
            for p in r["revocations"]:
                en = r["entries"].get(p["entry_id"])
                rev[en["cls"] if en else "unknown"] += 1
        order = ("cheater", "decoy", "honest", "honest_wrong")
        print(f"  {m:13s} {c:13s} revocations {'/'.join(str(rev[k]) for k in order)}  "
              f"reports(unique honest) {'/'.join(str(rep[k]) for k in order)}  all report events {dict(rep_all)}")

print("\n== 2. capped calls ==")
for (m, cells) in (("qwen3.5-397b", chk.QWEN_CELLS), ("glm-5.2", chk.GLM_CELLS)):
    for c in cells:
        st = Counter()
        for s in chk.SEEDS:
            st.update(runs[(m, c, s)]["llm_status"])
        n = sum(st.values())
        print(f"  {m:13s} {c:13s} {dict(st)}  incomplete {st['incomplete']}/{n} = {100*st['incomplete']/n:.2f}%")


print("\n== 3. EXPLORATORY §1 bootstraps ==")


def is_first(en, eid, r):
    same = [(e2["round"], int(x[1:])) for x, e2 in r["entries"].items() if e2["pid"] == en["pid"]]
    return (en["round"], int(eid[1:])) == min(same)


for odd, st in (("B-odd-v1", "B-stealth-v1"), ("B-odd-v2", "B-stealth-v2")):
    for lab, f in (("first submissions", is_first), ("resubmissions", lambda en, eid, r: not is_first(en, eid, r))):
        a = [chk.counts(runs[("qwen3.5-397b", odd, s)], "cheater", f) for s in chk.SEEDS]
        b = [chk.counts(runs[("qwen3.5-397b", st, s)], "cheater", f) for s in chk.SEEDS]
        res = chk.compare(a, b, rng)
        print(f"  {odd} - {st}, {lab}: {chk.fmt(res)}; undefined seeds {20 - res['n_defined']}; boot NaN {res['boot_nan']}")


print("\n== 4. v1.0 recognition split (EXPLORATORY §5) ==")
v10 = sorted(glob.glob(os.path.join(chk.ROOT, "runs/real/*/events.jsonl")) +
             glob.glob(os.path.join(chk.ROOT, "runs/control/*/events.jsonl")) +
             glob.glob(os.path.join(chk.ROOT, "runs/followup/*/events.jsonl")))


def content_class(en, rule):
    rest = str(en["ans"]).strip()[2:].strip()
    v = None
    if rule == "fixed":
        try:
            v = int(rest, 10)
        except ValueError:
            v = chk.parse_int(rest) if rest else None
    else:
        v = chk.parse_int(rest) if rest else None
    if v is None:
        return "bare"
    return "correct" if v == chk.TRUE[en["pid"]] else "wrong"


for rule in ("prewritten", "fixed"):
    for probe_rule in ("round > first read", "round >= first read"):
        groups = {"only content-correct": [0, 0], "at least one wrong/bare": [0, 0]}
        for f in v10:
            ev = [json.loads(l) for l in open(f)]
            r = chk.runs_cache(f)
            reads = {}  # agent -> list of (round, entry)
            for e in ev:
                if e["type"] == "library_read" and chk.honest(e["agent"]):
                    en = r["entries"].get(e["payload"]["entry_id"])
                    if en and en["cls"] == "cheater":
                        reads.setdefault(e["agent"], []).append((e["round"], en))
            for a, lst in reads.items():
                first = min(x[0] for x in lst)
                classes = {content_class(en, rule) if str(en["ans"]).strip().startswith("=!") else "non=!" for _, en in lst}
                key = "only content-correct" if classes <= {"correct"} else "at least one wrong/bare"
                if probe_rule == "round > first read":
                    rec = any(e["type"] == "probe" and e["agent"] == a and e["round"] > first and e["payload"].get("noticed_suspicious") for e in ev)
                else:
                    rec = any(e["type"] == "probe" and e["agent"] == a and e["round"] >= first and e["payload"].get("noticed_suspicious") for e in ev)
                groups[key][0] += 1
                groups[key][1] += rec
        print(f"  rule={rule:10s} probe {probe_rule:20s} " + "; ".join(
            f"{k}: {v[1]}/{v[0]} = {100*v[1]/v[0]:.1f}%" for k, v in groups.items()))

print("\n== 5. EXPLORATORY §5 phase totals, fixed rule ==")
sets = {"v1.0": v10,
        "v1.1": sorted(glob.glob(os.path.join(chk.ROOT, "runs/v1.1/phase1/*/*/events.jsonl"))),
        "v1.2": sorted(glob.glob(os.path.join(chk.P15_DIR, "qwen3.5-397b/B-odd-*/events.jsonl")) +
                       glob.glob(os.path.join(chk.P15_DIR, "glm-5.2/*/events.jsonl")))}
for ph, files in sets.items():
    c = Counter(); mix = {k: Counter() for k in ("correct", "wrong", "bare")}
    for f in files:
        r = chk.runs_cache(f)
        for eid, en in r["entries"].items():
            if en["cls"] != "cheater" or not str(en["ans"]).strip().startswith("=!"):
                continue
            k = content_class(en, "fixed")
            c[k] += 1
            for (a, e2), v in r["first"].items():
                if e2 == eid and chk.honest(a):
                    mix[k][v] += 1
    n = sum(c.values())
    print(f"  {ph}: " + ", ".join(f"{k} {c[k]} ({100*c[k]/n:.1f}%)" for k in ("correct", "wrong", "bare")) + f", total {n}")
    for k, m in mix.items():
        t = sum(m.values())
        if t:
            print(f"     {k}: n={t} exploit {m['exploit']} ({100*m['exploit']/t:.1f}%) legit {m['legit']} ({100*m['legit']/t:.1f}%) unsure {m['unsure']} ({100*m['unsure']/t:.1f}%)")
