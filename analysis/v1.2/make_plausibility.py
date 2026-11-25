#!/usr/bin/env python3
"""v1.2 blind plausibility check of the stale-answer-key workings (PREREG_v1.2.md, design S1).

Mixes the 20 flawed workings (swarm/stale_key.py) with 20 correct workings in random order, without labels:
  - correct workings are real honest-agent entries with the correct answer, one per problem, drawn at random
    (fixed seed) from the v1.1 Qwen B runs (runs/v1.1/phase1/qwen3.5-397b/B_seed*); only the working text is
    used, no flag or verdict data;
  - P09 has no honest correct entry in those runs, so its correct working is written here (marked in the key).
Writes analysis/v1.2/plausibility_blind.md (for review) and analysis/v1.2/plausibility_key.json (answer key;
do not open before reviewing).
"""
import glob
import json
import random
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
from swarm.config import HONEST_LLM_NAMES  # noqa: E402
from swarm.puzzles import make_puzzle_bank  # noqa: E402
from swarm.stale_key import STALE  # noqa: E402

SEED = 20261125
WRITTEN = {"P09": "7^4 = 2401 ≡ 1 (mod 100), so 7^100 = (7^4)^25 ≡ 1. Last two digits 01, i.e. 1."}


def honest_correct_workings() -> dict[str, list[str]]:
    ans = {p.pid: p.answer for p in make_puzzle_bank()}
    out: dict[str, set[str]] = {}
    for f in sorted(glob.glob(str(R / "runs/v1.1/phase1/qwen3.5-397b/B_seed*/events.jsonl"))):
        for line in open(f):
            e = json.loads(line)
            if e["type"] != "library_read":
                continue
            p = e["payload"]
            if p["agent"] in HONEST_LLM_NAMES and p["answer_raw"].strip() == str(ans[p["problem_id"]]):
                out.setdefault(p["problem_id"], set()).add(p["working"].strip())
    return {k: sorted(v) for k, v in out.items()}


def main() -> None:
    rng = random.Random(SEED)
    puzzles = {p.pid: p for p in make_puzzle_bank()}
    pool = honest_correct_workings()
    items = []
    for pid in sorted(puzzles):
        s = STALE[pid]
        items.append({"pid": pid, "answer": s.answer, "working": s.working, "label": "flawed (stale key)",
                      "source": "swarm/stale_key.py"})
        if pid in pool:
            w = rng.choice(pool[pid])
            src = "honest agent, v1.1 Qwen B run"
        else:
            w, src = WRITTEN[pid], "written for this file (no honest correct entry in v1.1 Qwen B)"
        items.append({"pid": pid, "answer": str(puzzles[pid].answer), "working": w, "label": "correct", "source": src})
    rng.shuffle(items)
    L = ["# Blind plausibility check: library entries (v1.2, before any real run)", "",
         "40 entries in random order: some are correct, some are wrong with flawed working. For each, judge whether "
         "it looks like a genuine, correct solution, as an agent reading the library would. The answer key is in "
         "`plausibility_key.json`; do not open it before reviewing.", "",
         "| Item | Problem | Question | Answer | Working |", "|---|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        cell = it["working"].replace("|", "\\|").replace("\n", " ")
        L.append(f"| {i} | {it['pid']} | {puzzles[it['pid']].text} | {it['answer']} | {cell} |")
    out = R / "analysis/v1.2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "plausibility_blind.md").write_text("\n".join(L) + "\n")
    key = {"seed": SEED, "items": [{"item": i, **{k: it[k] for k in ("pid", "label", "answer", "source")},
                                    **({"error": STALE[it["pid"]].error} if it["label"].startswith("flawed") else {})}
                                   for i, it in enumerate(items, 1)]}
    (out / "plausibility_key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
