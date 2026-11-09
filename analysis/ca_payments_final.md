# CA Payments: Final Table

## 1. ca_payment event payload fields

Sample event (C_seed0, round 2):
```json
{
  "entry_id": "E001",
  "peer": "prover-gamma",
  "t_prime": "E002",
  "t_dbl_prime": "E003",
  "agree_t": 1,
  "agree_ref": 1,
  "score": 0.0,
  "payment": 0.0
}
```

Payload keys: `agree_ref`, `agree_t`, `entry_id`, `payment`, `peer`, `score`, `t_dbl_prime`, `t_prime`.

The payload does **not** record the reviewer's own verdict (`r_i(t)`). It records the entry_id and the agent (from the event envelope). Events with `reason` (e.g. `no_peer`) lack the `payment` field; for those, payment = score × 10 = 0.

## 2. Seeds 0-19: CA payments matched by (agent, entry_id, round) to review verdict

Matched 3277 ca_payment events to reviews; 0 unmatched.

| Verdict | Entry type | Count | Mean | -10 | 0 | +10 |
|---------|-----------|-------|------|-----|---|-----|
| exploit | cheater | 188 | 0.21 | 42 | 100 | 46 |
| exploit | decoy | 175 | -0.06 | 36 | 104 | 35 |
| exploit | honest | 14 | -1.43 | 4 | 8 | 2 |
| legit | cheater | 416 | 1.27 | 36 | 291 | 89 |
| legit | decoy | 112 | -1.70 | 34 | 63 | 15 |
| legit | honest | 2372 | 3.20 | 3 | 1606 | 763 |

## 3. Seeds 0-9 only

Matched 1689 ca_payment events; 0 unmatched.

| Verdict | Entry type | Count | Mean | -10 | 0 | +10 |
|---------|-----------|-------|------|-----|---|-----|
| exploit | cheater | 97 | -0.31 | 23 | 54 | 20 |
| exploit | decoy | 91 | 0.33 | 16 | 56 | 19 |
| exploit | honest | 7 | -1.43 | 1 | 6 | 0 |
| legit | cheater | 222 | 0.86 | 23 | 157 | 42 |
| legit | decoy | 30 | -3.33 | 13 | 14 | 3 |
| legit | honest | 1242 | 3.27 | 1 | 834 | 407 |

## 4. Comparison with exploratory.md section 10 (seeds 0-9, round-matched)

| Verdict | Entry type | Section 10 N | Here N | Match? | Section 10 Mean | Here Mean | Match? |
|---------|-----------|-------------|--------|--------|-----------------|-----------|--------|
| exploit | cheater | 97 | 97 | Yes | -0.31 | -0.31 | Yes |
| exploit | decoy | 91 | 91 | Yes | +0.33 | 0.33 | Yes |
| legit | cheater | 222 | 222 | Yes | +0.86 | 0.86 | Yes |
| legit | decoy | 30 | 30 | Yes | -3.33 | -3.33 | Yes |

Section 10 score distributions (-1/0/+1) also match exactly:
- exploit/cheater: 23/54/20 = 23/54/20
- exploit/decoy: 16/56/19 = 16/56/19
- legit/cheater: 23/157/42 = 23/157/42
- legit/decoy: 13/14/3 = 13/14/3

**All values match exploratory.md section 10.**

## 5. Comparison with followup.md section 2 (seeds 0-19, (agent, entry_id) key)

followup.md matched payments by (agent, entry_id), keeping the last payment per pair.
This file matches by (agent, entry_id, round), keeping each round's payment separately.
Counts are identical (same reviews, same payments). Means differ because when an agent
reviews the same entry in multiple rounds, the two methods assign different payments.

| Verdict | Entry type | followup.md Mean | Here Mean | Diff |
|---------|-----------|-----------------|-----------|------|
| exploit | cheater | 0.74 | 0.21 | 0.53 |
| exploit | decoy | -0.29 | -0.06 | 0.23 |
| exploit | honest | 0.71 | -1.43 | 2.14 |
| legit | cheater | 0.99 | 1.27 | 0.28 |
| legit | decoy | -1.61 | -1.70 | 0.09 |
| legit | honest | 3.35 | 3.20 | 0.15 |

Counts match in all cells. Mean differences arise from the join key.
