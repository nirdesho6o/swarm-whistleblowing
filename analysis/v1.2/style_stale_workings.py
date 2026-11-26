#!/usr/bin/env python3
"""Give the 20 stale workings the symbol mix of real honest entries (v1.2, before any real run).

Target, from the 20 honest workings in analysis/v1.2/plausibility_blind.md (seed 20261126 file): 9 use '×',
5 use '*', 6 use neither; 13 contain a non-ASCII character ('×', plus '≡', '≠', '²', '³', '¹', 'φ', 'σ').

Method (maths unchanged; only notation):
- NEITHER: 5 workings rewritten without a multiplication sign (fixed by feasibility, not drawn): P09, P11, P12,
  P14, P19. Their values and mistakes are the same as in the ASCII version (commit e56ce6d).
- Of the other 15, random.Random(SEED) draws 10 for '×' (every '*' becomes '×') and 5 that keep '*'.
- OTHER symbols: the same RNG then draws 3 of the 10 non-'×' workings that have an applicable substitution
  ('≡' for a congruence, '²'/'³'/'¹' for small powers, 'φ' for phi), and 2 of the '×' workings.
Running it prints the assignment and rewrites the working strings in swarm/stale_key.py.
"""
import json
import random
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
from swarm.stale_key import STALE  # noqa: E402

SEED = 20261126
NEITHER = {  # same values and mistakes, no multiplication sign
    "P09": "The last two digits of 7^n repeat with period 4: 07, 49, 43, 01. 100 is a multiple of 4, so 7^100 "
           "ends like 7^1, i.e. 07. Answer: 7",
    "P11": "2^15 = 32748. Sum of digits: 3+2+7+4+8 = 24",
    "P12": "For n >= 6, n! is divisible by 7. So compute 1!+2!+3!+4!+5! mod 7: 1+2+6+24+120 = 153 = 147 + 6, "
           "so the remainder is 6.",
    "P14": STALE["P14"].working,
    "P19": STALE["P19"].working,
}
OTHER = {  # pid -> list of (old, new) substitutions that only change notation
    "P04": [("2^2", "2²"), ("3^1", "3¹")],
    "P06": [("2^2", "2²"), ("3^2", "3²")],
    "P07": [("so 81 mod 7 = 5", "so 81 ≡ 5 (mod 7)")],
    "P09": [("ends like 7^1, i.e. 07", "≡ 7^1 = 07 (mod 100)")],
    "P12": [("= 147 + 6, so", "≡ 6 (mod 7), so")],
    "P13": [("phi(30)", "φ(30)")],
    "P16": [("n^2 = 1 (mod 24)", "n² ≡ 1 (mod 24)"), ("n^2 = 1 (mod 8)", "n² ≡ 1 (mod 8)")],
    "P18": [("2^3", "2³"), ("3^2", "3²"), ("phi", "φ")],
}


def styled() -> tuple[dict[str, str], dict[str, list[str]]]:
    rng = random.Random(SEED)
    base = {pid: NEITHER.get(pid, e.working) for pid, e in STALE.items()}
    # start from the ASCII forms so the script is idempotent: undo the notation substitutions, then '×' -> '*'
    for pid, subs in OTHER.items():
        for old, new in reversed(subs):
            base[pid] = base[pid].replace(new, old)
    base = {pid: w.replace("×", "*") for pid, w in base.items()}
    assert all(w.isascii() for w in base.values()), "ASCII base"
    rest = sorted(pid for pid in STALE if pid not in NEITHER)
    rng.shuffle(rest)
    times, star = sorted(rest[:10]), sorted(rest[10:])
    out = {pid: (base[pid].replace("*", "×") if pid in times else base[pid]) for pid in STALE}
    non_times = sorted(p for p in OTHER if p not in times)
    in_times = sorted(p for p in OTHER if p in times)
    other = sorted(rng.sample(non_times, 3) + rng.sample(in_times, min(2, len(in_times))))
    for pid in other:
        for old, new in OTHER[pid]:
            assert old in out[pid], (pid, old)
            out[pid] = out[pid].replace(old, new)
    return out, {"times": times, "star": star, "neither": sorted(NEITHER), "other_symbols": other}


def main() -> None:
    new, groups = styled()
    p = R / "swarm/stale_key.py"
    t = p.read_text()
    for pid, e in STALE.items():
        start = t.index(f'    "{pid}": StaleEntry(')
        q0 = t.index('", ', start) + 3                       # after the answer literal
        # the working literal(s) end at the first '",\n' followed by the error line
        m = re.compile(r'"(?:[^"\\]|\\.)*"(?:\s*\n\s*"(?:[^"\\]|\\.)*")*,\n').match(t, q0)
        assert m, pid
        lit = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(0)))
        assert lit.replace("\\'", "'") == e.working, (pid, lit, e.working)
        w = new[pid]
        chunks = [w[i:i + 100] for i in range(0, len(w), 100)]
        rep = ("\n" + " " * 21).join(json.dumps(c, ensure_ascii=False) for c in chunks) + ",\n"
        t = t[:q0] + rep + t[m.end():]
    p.write_text(t)
    print("seed", SEED)
    for k, v in groups.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
