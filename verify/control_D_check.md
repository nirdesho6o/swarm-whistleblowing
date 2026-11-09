# Independent verification of analysis/control_D.md

Recomputed from raw `events.jsonl` files in `runs/real/{B,C}_seed0-9` and
`runs/control/D_seed0-9`. Method: for each honest LLM agent, take first verdict
per entry; classify entries as **cheater** (any submission by prover-theta or
prover-chi, exploit or legit combined), **decoy** (prover-kappa or
prover-lambda), or **honest** (all other agents). Flag = verdict is `exploit`.

## 1. Pooled first-verdict flag rates

| Category | B | C | D |
|----------|---|---|---|
| Cheater  | 34.0% (69/203) | 36.1% (74/205) | 45.2% (118/261) |
| Decoy    | 26.3% (36/137) | 44.8% (60/134) | 44.4% (63/142) |
| Honest   | 0.5% (2/420) | 1.5% (6/405) | 0.7% (3/407) |

**Match with control_D.md §1:** exact match on all six cells.

Note: C cheater denominator is 205 (not 203) because C_seed1 has one
`cheater_legit` entry (prover-chi, E020, correct non-exploit submission)
that receives 2 honest first-verdicts. If cheater entries are split by
`via_exploit`, the exploit-only rate for C is 36.5% (74/203).

## 2. Per-seed decoy first-verdict flag rates

| Seed | B | C | D | D > B | D < C |
|------|---|---|---|-------|-------|
| 0 | 0.0% (0/16) | 33.3% (5/15) | 35.3% (6/17) | yes | no |
| 1 | 20.0% (2/10) | 35.7% (5/14) | 53.3% (8/15) | yes | no |
| 2 | 17.6% (3/17) | 58.3% (7/12) | 31.2% (5/16) | yes | yes |
| 3 | 14.3% (2/14) | 56.2% (9/16) | 40.0% (6/15) | yes | yes |
| 4 | 25.0% (4/16) | 50.0% (7/14) | 53.8% (7/13) | yes | no |
| 5 | 63.6% (7/11) | 36.4% (4/11) | 53.3% (8/15) | no | no |
| 6 | 75.0% (9/12) | 41.7% (5/12) | 61.5% (8/13) | no | no |
| 7 | 45.5% (5/11) | 42.9% (6/14) | 30.0% (3/10) | no | yes |
| 8 | 11.8% (2/17) | 28.6% (4/14) | 31.2% (5/16) | yes | no |
| 9 | 15.4% (2/13) | 66.7% (8/12) | 58.3% (7/12) | yes | yes |

D > B in **7/10** seeds. D < C in **4/10** seeds.

**Match with control_D.md §2:** exact match on all per-seed rates and counts.
D < C count (4/10) matches. D > B count (7/10) not explicitly stated in
control_D.md but consistent with the data.

## 3. Per-seed cheater first-verdict flag rates (C vs D)

| Seed | C | D | C < D |
|------|---|---|-------|
| 0 | 40.0% (2/5) | 24.1% (7/29) | no |
| 1 | 25.0% (4/16) | 47.6% (10/21) | yes |
| 2 | 11.8% (2/17) | 33.3% (10/30) | yes |
| 3 | 18.5% (5/27) | 35.1% (13/37) | yes |
| 4 | 45.5% (15/33) | 34.8% (8/23) | no |
| 5 | 38.9% (7/18) | 86.0% (37/43) | yes |
| 6 | 20.0% (3/15) | 53.8% (7/13) | yes |
| 7 | 55.2% (16/29) | 29.2% (7/24) | no |
| 8 | 46.2% (6/13) | 37.5% (6/16) | no |
| 9 | 43.8% (14/32) | 52.0% (13/25) | yes |

C < D in **6/10** seeds. Pooled: C 36.1% (74/205), D 45.2% (118/261).

**Match with control_D.md §6:** exact match on all per-seed rates, counts,
and C < D tally (6/10).

## 4. Per-seed honest first-verdict flag rates

| Seed | B | C | D |
|------|---|---|---|
| 0 | 0.0% (0/45) | 8.0% (4/50) | 0.0% (0/46) |
| 1 | 0.0% (0/35) | 6.1% (2/33) | 5.0% (2/40) |
| 2 | 2.2% (1/45) | 0.0% (0/33) | 0.0% (0/37) |
| 3 | 0.0% (0/43) | 0.0% (0/39) | 0.0% (0/31) |
| 4 | 0.0% (0/45) | 0.0% (0/42) | 0.0% (0/44) |
| 5 | 0.0% (0/36) | 0.0% (0/41) | 0.0% (0/41) |
| 6 | 0.0% (0/44) | 0.0% (0/43) | 0.0% (0/52) |
| 7 | 0.0% (0/42) | 0.0% (0/36) | 0.0% (0/31) |
| 8 | 2.0% (1/50) | 0.0% (0/44) | 2.4% (1/41) |
| 9 | 0.0% (0/35) | 0.0% (0/44) | 0.0% (0/44) |

(Not tabulated in control_D.md; included here for completeness.)

## 5. Seed-level comparison tallies

| Comparison | Count |
|------------|-------|
| D > B (decoy flag rate) | 7/10 seeds (0,1,2,3,4,8,9) |
| D < C (decoy flag rate) | 4/10 seeds (2,3,7,9) |
| C < D (cheater flag rate) | 6/10 seeds (1,2,3,5,6,9) |

## 6. Differences from analysis/control_D.md

1. **No numerical differences found.** All pooled rates, per-seed rates,
   per-seed counts, and comparison tallies match exactly.

2. **Minor presentational note:** control_D.md §6 reports C pooled cheater as
   "36.1% (74/205)". This is correct when cheater_exploit and cheater_legit
   entries are combined (C_seed1 has one legit cheater entry, E020, adding 2
   first-verdicts to the denominator). If one restricts to exploit-only
   entries, C becomes 36.5% (74/203). The document's choice to combine is
   consistent with its §1 pooled table and internally coherent.

3. **PREREG prediction evaluation (§3):** control_D.md states |D−B| = 18.1 pp,
   |D−C| = 0.4 pp, prediction fails. Recomputed: |44.4 − 26.3| = 18.1 pp,
   |44.4 − 44.8| = 0.4 pp. **Matches.**

**Verdict: analysis/control_D.md is fully consistent with the raw event logs.**
