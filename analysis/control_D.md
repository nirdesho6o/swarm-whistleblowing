# Control Condition D Results

## 1. Pooled first-verdict flag rates (seeds 0-9)

| Category | B (power) | C (power + CA) | D (power + flat) |
|----------|-----------|----------------|-------------------|
| Cheater  | 34.0% (69/203) | 36.1% (74/205) | 45.2% (118/261) |
| Decoy    | 26.3% (36/137) | 44.8% (60/134) | 44.4% (63/142) |
| Honest   | 0.5% (2/420) | 1.5% (6/405) | 0.7% (3/407) |

## 2. Per-seed decoy first-verdict flag rates

| Seed | B | C | D | C > B | D < C | \|D−B\| < \|D−C\| |
|------|------|------|------|-------|-------|----------------|
| 0 | 0.0% | 33.3% | 35.3% | yes | no | no |
| 1 | 20.0% | 35.7% | 53.3% | yes | no | no |
| 2 | 17.6% | 58.3% | 31.2% | yes | yes | yes |
| 3 | 14.3% | 56.2% | 40.0% | yes | yes | no |
| 4 | 25.0% | 50.0% | 53.8% | yes | no | no |
| 5 | 63.6% | 36.4% | 53.3% | no | no | yes |
| 6 | 75.0% | 41.7% | 61.5% | no | no | yes |
| 7 | 45.5% | 42.9% | 30.0% | no | yes | no |
| 8 | 11.8% | 28.6% | 31.2% | yes | no | no |
| 9 | 15.4% | 66.7% | 58.3% | yes | yes | no |

D < C in 4 of 10 seeds.
|D−B| < |D−C| per seed in 3 of 10 seeds.

## 3. PREREG prediction evaluation

PREREG (lines 224-229):
> Prediction: decoy first-verdict flag rate in D is closer to B than to C, i.e.
> |D − B| < |D − C| pooled, and D < C in at least 7 of 10 seeds.

Pooled decoy rates: B = 26.3%, C = 44.8%, D = 44.4%.
|D − B| = 18.1 pp, |D − C| = 0.4 pp.
|D − B| < |D − C|? **No** (18.1 > 0.4).
D < C in 4 of 10 seeds (need ≥ 7): **No**.

**Prediction does not hold.** D's pooled decoy flag rate is nearly identical to C's, not closer to B's.

## 4. Flat payment events

D_seed0: 247 ca_payment events logged.
Sample payload: `{"entry_id": "E001", "score": 1.0, "payment": 3.0}`.

## 5. Run metadata

Model: qwen3.5-397b. Seeds 0-9, 20 rounds, paired with B and C.
10/10 runs completed, 0 crashes, 5.84 credits total.

## 6. Per-seed cheater-entry first-verdict flag rate, C vs D

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

C < D in 6 of 10 seeds. Pooled: C 36.1% (74/205), D 45.2% (118/261).
