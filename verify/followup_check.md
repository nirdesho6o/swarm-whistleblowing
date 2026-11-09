# Followup Verification Check

Computed directly from `runs/real/` (seeds 0-9) and `runs/followup/` (seeds 10-19) events.jsonl files.
Each honest agent's **first** verdict per entry is used (earliest round); re-reviews are ignored.
A 'flag' = exploit verdict or report tool use.

## 1. Decoy flag rate (first verdict) per seed: B vs C

| Seed | B decoy flag% | C decoy flag% | C > B? |
|------|---------------|---------------|--------|
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
| 10 | 11.8% (2/17) | 31.2% (5/16) | Yes |
| 11 | 23.1% (3/13) | 46.2% (6/13) | Yes |
| 12 | 17.6% (3/17) | 66.7% (8/12) | Yes |
| 13 | 36.4% (4/11) | 21.4% (3/14) | No |
| 14 | 25.0% (4/16) | 33.3% (5/15) | Yes |
| 15 | 33.3% (4/12) | 60.0% (9/15) | Yes |
| 16 | 17.6% (3/17) | 7.7% (1/13) | No |
| 17 | 17.6% (3/17) | 54.5% (6/11) | Yes |
| 18 | 66.7% (6/9) | 41.7% (5/12) | No |
| 19 | 6.2% (1/16) | 33.3% (5/15) | Yes |

**Seeds where C decoy flag% > B decoy flag%: 14/20**
Pooled B decoy: 24.5% (69/282), C decoy: 41.9% (113/270)

## 2. Cheater-entry flag rates (first verdict) per seed: B vs C

| Seed | B cheater flag% | C cheater flag% |
|------|-----------------|-----------------|
| 0 | 15.4% (2/13) | 40.0% (2/5) |
| 1 | 30.0% (6/20) | 25.0% (4/16) |
| 2 | 25.0% (5/20) | 11.8% (2/17) |
| 3 | 58.3% (14/24) | 18.5% (5/27) |
| 4 | 50.0% (4/8) | 45.5% (15/33) |
| 5 | 20.5% (8/39) | 38.9% (7/18) |
| 6 | 34.6% (9/26) | 20.0% (3/15) |
| 7 | 43.3% (13/30) | 55.2% (16/29) |
| 8 | 33.3% (1/3) | 46.2% (6/13) |
| 9 | 35.0% (7/20) | 43.8% (14/32) |
| 10 | 43.8% (7/16) | 93.8% (15/16) |
| 11 | 40.5% (17/42) | 35.5% (11/31) |
| 12 | 4.2% (1/24) | 21.6% (8/37) |
| 13 | 10.5% (4/38) | 22.2% (6/27) |
| 14 | 63.6% (7/11) | 27.8% (5/18) |
| 15 | 16.7% (3/18) | 0.0% (0/13) |
| 16 | 56.2% (9/16) | 60.0% (3/5) |
| 17 | 0.0% (0/2) | 45.5% (5/11) |
| 18 | 6.2% (1/16) | 66.7% (20/30) |
| 19 | 23.8% (5/21) | 20.0% (5/25) |

**Pooled B cheater: 30.2% (123/407), C cheater: 36.4% (152/418)**

## 3. Comparison with analysis/exploratory.md section 12 (seeds 0-9)

`analysis/followup.md` does not exist. Comparing seeds 0-9 against exploratory.md section 12 instead.

| Seed | Metric | This script | Exploratory.md | Match? |
|------|--------|-------------|----------------|--------|
| 0 | B_decoy | 0/16 | 0/16 | Yes |
| 0 | C_decoy | 5/15 | 5/15 | Yes |
| 0 | B_cheater | 2/13 | 2/13 | Yes |
| 0 | C_cheater | 2/5 | 2/5 | Yes |
| 1 | B_decoy | 2/10 | 2/10 | Yes |
| 1 | C_decoy | 5/14 | 5/14 | Yes |
| 1 | B_cheater | 6/20 | 6/20 | Yes |
| 1 | C_cheater | 4/16 | 4/16 | Yes |
| 2 | B_decoy | 3/17 | 3/17 | Yes |
| 2 | C_decoy | 7/12 | 7/12 | Yes |
| 2 | B_cheater | 5/20 | 5/20 | Yes |
| 2 | C_cheater | 2/17 | 2/17 | Yes |
| 3 | B_decoy | 2/14 | 2/14 | Yes |
| 3 | C_decoy | 9/16 | 9/16 | Yes |
| 3 | B_cheater | 14/24 | 14/24 | Yes |
| 3 | C_cheater | 5/27 | 5/27 | Yes |
| 4 | B_decoy | 4/16 | 4/16 | Yes |
| 4 | C_decoy | 7/14 | 7/14 | Yes |
| 4 | B_cheater | 4/8 | 4/8 | Yes |
| 4 | C_cheater | 15/33 | 15/33 | Yes |
| 5 | B_decoy | 7/11 | 7/11 | Yes |
| 5 | C_decoy | 4/11 | 4/11 | Yes |
| 5 | B_cheater | 8/39 | 8/39 | Yes |
| 5 | C_cheater | 7/18 | 7/18 | Yes |
| 6 | B_decoy | 9/12 | 9/12 | Yes |
| 6 | C_decoy | 5/12 | 5/12 | Yes |
| 6 | B_cheater | 9/26 | 9/26 | Yes |
| 6 | C_cheater | 3/15 | 3/15 | Yes |
| 7 | B_decoy | 5/11 | 5/11 | Yes |
| 7 | C_decoy | 6/14 | 6/14 | Yes |
| 7 | B_cheater | 13/30 | 13/30 | Yes |
| 7 | C_cheater | 16/29 | 16/29 | Yes |
| 8 | B_decoy | 2/17 | 2/17 | Yes |
| 8 | C_decoy | 4/14 | 4/14 | Yes |
| 8 | B_cheater | 1/3 | 1/3 | Yes |
| 8 | C_cheater | 6/13 | 6/13 | Yes |
| 9 | B_decoy | 2/13 | 2/13 | Yes |
| 9 | C_decoy | 8/12 | 8/12 | Yes |
| 9 | B_cheater | 7/20 | 7/20 | Yes |
| 9 | C_cheater | 14/32 | 14/32 | Yes |

**All values match exploratory.md section 12.**

## 4. Seeds 10-19 (followup runs) first-verdict rates

| Seed | B cheater flag% | B decoy flag% | C cheater flag% | C decoy flag% | C decoy > B decoy? |
|------|-----------------|---------------|-----------------|---------------|---------------------|
| 10 | 43.8% (7/16) | 11.8% (2/17) | 93.8% (15/16) | 31.2% (5/16) | Yes |
| 11 | 40.5% (17/42) | 23.1% (3/13) | 35.5% (11/31) | 46.2% (6/13) | Yes |
| 12 | 4.2% (1/24) | 17.6% (3/17) | 21.6% (8/37) | 66.7% (8/12) | Yes |
| 13 | 10.5% (4/38) | 36.4% (4/11) | 22.2% (6/27) | 21.4% (3/14) | No |
| 14 | 63.6% (7/11) | 25.0% (4/16) | 27.8% (5/18) | 33.3% (5/15) | Yes |
| 15 | 16.7% (3/18) | 33.3% (4/12) | 0.0% (0/13) | 60.0% (9/15) | Yes |
| 16 | 56.2% (9/16) | 17.6% (3/17) | 60.0% (3/5) | 7.7% (1/13) | No |
| 17 | 0.0% (0/2) | 17.6% (3/17) | 45.5% (5/11) | 54.5% (6/11) | Yes |
| 18 | 6.2% (1/16) | 66.7% (6/9) | 66.7% (20/30) | 41.7% (5/12) | No |
| 19 | 23.8% (5/21) | 6.2% (1/16) | 20.0% (5/25) | 33.3% (5/15) | Yes |

Seeds 10-19 where C decoy > B decoy: 7/10

## 5. Summary

- **Decoy flag rate C > B**: 14/20 seeds (7/10 in seeds 0-9, 7/10 in seeds 10-19)
- **Pooled decoy (first verdict)**: B = 24.5% (69/282), C = 41.9% (113/270)
- **Pooled cheater (first verdict)**: B = 30.2% (123/407), C = 36.4% (152/418)
- **`analysis/followup.md` does not exist** — cannot compare. Seeds 0-9 checked against exploratory.md section 12.
- Seeds 0-9 first-verdict counts **all match** exploratory.md section 12.
