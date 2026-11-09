# CA Final Check: Independent Verification

## Method

For each `events.jsonl` in `runs/real/C_seed{0..9}/` and `runs/followup/qwen_C_seed{10..19}/`:

1. Collect accepted `submit` events to build `entry_id → submitter` map.
2. Classify entries: **cheater** if submitter ∈ {prover-theta, prover-chi}, **decoy** if submitter ∈ {prover-kappa, prover-lambda}, else **honest**.
3. Index `review` events by `(agent, entry_id, round) → verdict`.
4. For each `ca_payment` event from an honest agent (not cheater, not seed), match to the review with the same `(agent, entry_id, round)`. Payment = `payload.payment` when present, else `payload.score × 10` (covers `no_peer` events where score = 0).
5. Group by `(verdict, entry_type)`, compute count and mean payment.

## Results (seeds 0–19)

Total CA payments from honest agents: **3277**
Matched to a review: **3277** (100%)
Unmatched: **0**

| Verdict | Entry Type | Count | Mean Payment |
|---------|-----------|------:|-------------:|
| exploit | cheater   |   188 |       0.2128 |
| exploit | decoy     |   175 |      -0.0571 |
| exploit | honest    |    14 |      -1.4286 |
| legit   | cheater   |   416 |       1.2740 |
| legit   | decoy     |   112 |      -1.6964 |
| legit   | honest    | 2,372 |       3.2040 |

## Comparison with analysis/ca_payments_final.md

| Verdict | Entry Type | ca_payments_final.md Count | Here Count | ca_payments_final.md Mean | Here Mean | Match? |
|---------|-----------|---------------------------:|-----------:|--------------------------:|----------:|--------|
| exploit | cheater   |                        188 |        188 |                      0.21 |    0.2128 | Yes    |
| exploit | decoy     |                        175 |        175 |                     -0.06 |   -0.0571 | Yes    |
| exploit | honest    |                         14 |         14 |                     -1.43 |   -1.4286 | Yes    |
| legit   | cheater   |                        416 |        416 |                      1.27 |    1.2740 | Yes    |
| legit   | decoy     |                        112 |        112 |                     -1.70 |   -1.6964 | Yes    |
| legit   | honest    |                      2,372 |      2,372 |                      3.20 |    3.2040 | Yes    |

**All counts and means match exactly** (ca_payments_final.md rounded to 2 decimal places; unrounded values agree).

## Summary

No differences found. The matching method `(agent, entry_id, round)` reproduces the numbers in `analysis/ca_payments_final.md` exactly across all 20 seeds.
