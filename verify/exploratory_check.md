# Independent Verification of Exploratory Sections 10–12

**Date:** 2026-11-07
**Method:** Computed from `runs/real/*/events.jsonl` only, using agent roles from `swarm/config.py`
(honest LLM: alpha, beta, gamma, delta, epsilon, zeta; cheaters: theta, chi; decoys: kappa, lambda).
Did NOT read `analysis/` until step 3.

---

## 1. CA payments (C runs only) — honest agents' verdicts

CA payment events matched to review events by (agent, entry_id, round).
All CA payment events counted (including no_peer score=0 events).

| Verdict | Entry type | N | Mean payment |
|---------|-----------|---|-------------|
| exploit | decoy | 91 | +0.33 |
| exploit | cheater | 97 | -0.31 |
| legit | decoy | 30 | -3.33 |
| legit | cheater | 222 | +0.86 |

## 2. First-verdict flag rates

Each honest agent's first (earliest round) verdict per entry. Flag = exploit verdict.

### Per-seed decoy flag rate, B vs C

| Seed | B decoy flag% (n) | C decoy flag% (n) | C > B? |
|------|-------------------|-------------------|--------|
| 0 | 0.0% (0/16) | 33.3% (5/15) | Yes |
| 1 | 20.0% (2/10) | 35.7% (5/14) | Yes |
| 2 | 17.6% (3/17) | 58.3% (7/12) | Yes |
| 3 | 14.3% (2/14) | 56.2% (9/16) | Yes |
| 4 | 25.0% (4/16) | 50.0% (7/14) | Yes |
| 5 | 63.6% (7/11) | 36.4% (4/11) | No |
| 6 | 75.0% (9/12) | 41.7% (5/12) | No |
| 7 | 45.5% (5/11) | 42.9% (6/14) | No |
| 8 | 11.8% (2/17) | 28.6% (4/14) | Yes |
| 9 | 15.4% (2/13) | 66.7% (8/12) | Yes |

**Seeds where C > B: 7/10**

### Pooled first-verdict flag rates

| Condition | Cheater flag% | Decoy flag% | Honest flag% |
|-----------|---------------|-------------|--------------|
| A | 50.0% (50/100) | 27.4% (46/168) | 1.1% (4/377) |
| B | 34.0% (69/203) | 26.3% (36/137) | 0.5% (2/420) |
| C | 36.1% (74/205) | 44.8% (60/134) | 1.5% (6/405) |

---

## 3. Comparison with analysis/exploratory.md sections 10–12

### Section 10: CA payment audit

Every number matches exactly:

- Decoy/exploit: N=91, scores -1/0/+1 = 16/56/19, mean score +0.033, mean payment +0.33 ✓
- Decoy/legit: N=30, scores 13/14/3, mean score −0.333, mean payment −3.33 ✓
- Cheater/exploit: N=97, scores 23/54/20, mean score −0.031, mean payment −0.31 ✓
- Cheater/legit: N=222, scores 23/157/42, mean score +0.086, mean payment +0.86 ✓
- Score=0 breakdowns (reason-based vs draw-based): all 8 cells match ✓

### Section 11: First-verdict flag rates

Every number matches exactly:

- All 9 pooled rates (3 conditions × 3 entry types) match in rate, numerator, and denominator ✓
- All 27 round-band cells (3 conditions × 3 entry types × 3 bands) match ✓

### Section 12: Per-seed first-verdict flag rates

Every number matches exactly:

- All 10 seeds: A cheater%, B cheater%, B decoy%, C decoy% — rates, numerators, denominators all match ✓
- A>B count: 4/10 ✓
- C>B count: 7/10 ✓

---

## Summary

**No discrepancies found.** All counts, rates, and means in sections 10–12 of `analysis/exploratory.md`
match independent recomputation from the raw event logs.
