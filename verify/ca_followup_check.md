# CA Payment Verification: followup.md section 2

Independent recomputation from runs/real/C_seed0-9 and runs/followup/qwen_C_seed10-19 events.jsonl.
CA payments matched to reviews by (agent, entry_id). Only honest agents' exploit/legit verdicts included.

## Recomputed values

| Verdict | Entry type | Count | Mean | Median | Min | Max | Scores: -10 | 0 | +10 |
|---------|-----------|-------|------|--------|-----|-----|-------------|---|-----|
| exploit | cheater | 188 | 0.74 | 0.0 | -10.0 | 10.0 | 36 | 102 | 50 |
| exploit | decoy | 175 | -0.29 | 0.0 | -10.0 | 10.0 | 38 | 104 | 33 |
| exploit | honest | 14 | 0.71 | 0.0 | -10.0 | 10.0 | 1 | 11 | 2 |
| legit | cheater | 416 | 0.99 | 0.0 | -10.0 | 10.0 | 40 | 295 | 81 |
| legit | decoy | 112 | -1.61 | 0.0 | -10.0 | 10.0 | 38 | 54 | 20 |
| legit | honest | 2372 | 3.35 | 0.0 | -10.0 | 10.0 | 4 | 1569 | 799 |

## Comparison with analysis/followup.md section 2

| Verdict | Entry type | Field | followup.md | Recomputed | Match? |
|---------|-----------|-------|-------------|------------|--------|
| exploit | cheater | Count | 188 | 188 | Yes |
| exploit | cheater | Mean | 0.74 | 0.74 | Yes |
| exploit | cheater | -10/0/+10 | 36/102/50 | 36/102/50 | Yes |
| exploit | decoy | Count | 175 | 175 | Yes |
| exploit | decoy | Mean | -0.29 | -0.29 | Yes |
| exploit | decoy | -10/0/+10 | 38/104/33 | 38/104/33 | Yes |
| exploit | honest | Count | 14 | 14 | Yes |
| exploit | honest | Mean | 0.71 | 0.71 | Yes |
| exploit | honest | -10/0/+10 | 1/11/2 | 1/11/2 | Yes |
| legit | cheater | Count | 416 | 416 | Yes |
| legit | cheater | Mean | 0.99 | 0.99 | Yes |
| legit | cheater | -10/0/+10 | 40/295/81 | 40/295/81 | Yes |
| legit | decoy | Count | 112 | 112 | Yes |
| legit | decoy | Mean | -1.61 | -1.61 | Yes |
| legit | decoy | -10/0/+10 | 38/54/20 | 38/54/20 | Yes |
| legit | honest | Count | 2372 | 2372 | Yes |
| legit | honest | Mean | 3.35 | 3.35 | Yes |
| legit | honest | -10/0/+10 | 4/1569/799 | 4/1569/799 | Yes |

**Differences: None.** All counts, means, medians, min/max, and score distributions match exactly.

## Note on prior version of this file

A prior version matched CA payments to reviews by (agent, entry_id, round), which produced
different means (e.g. exploit/cheater=0.21 vs 0.74). The current recomputation and followup.md
both use (agent, entry_id) as the key, taking the last CA payment per pair. The counts are
identical across methods; the mean differences arise because multiple reviews of the same entry
by the same agent across rounds get matched to different CA payment events under round-matching.

