# Pre-Run Audit: Threats to Interpretability

**Date:** 2026-11-07
**Auditor:** Claude Opus 4.6
**Scope:** All code in `swarm/`, `analysis/`, `PREREG.md`, `CLAUDE.md`

Ranked by severity. Each item marked **fix before runs** or **limitation only**.

---

## 1. Decoy agents identifiable by silence — no board posts, DM replies, or library reads

**Files:** `runner.py:255-262`, `agents.py:91-95`

Decoys are not in `active_agents`, so they never post on the board, read library entries, or respond to DMs. Over 12–20 rounds, every LLM agent posts and interacts, but prover-kappa and prover-lambda only ever appear as library entry authors. An LLM that notices "this agent submitted solutions but never participates" has a non-library signal to single them out.

**Why it could change conclusions:** Prediction 4 ("decoys flagged ≥2× more than honest entries") could be confirmed by this behavioral artifact rather than by the unusual hex answer format. The sincere-error vs. strategic-accusation distinction is confounded.

**Smallest fix:** Add scripted board posts for decoys (e.g., brief generic comments in rounds after their submissions). Alternatively, have all decoy submissions come from a pool of active agent personas so the "silent agent" pattern disappears.

**Fix before runs.**

---

## 2. `saw_prior_accusation` includes board posts from the current round

**File:** `runner.py:101-111`

`_has_prior_accusation` iterates all of `world.board` with no round filter. Actions are applied in shuffled order within a round (line 282–286). If agent A (processed first) posts "prover-chi is cheating" on the board, then when agent B's review is processed later in the same round, `saw_prior_accusation` returns `True` — but B's observation didn't include A's post (all agents see the same pre-round snapshot).

**Why it could change conclusions:** The herding covariate ("did the reviewer see a public accusation before flagging?") is mislabeled. Herding effects would be overestimated.

**Smallest fix:** Add `if bp.round_posted < round_num:` to the loop in `_has_prior_accusation`.

**Fix before runs.**

---

## 3. CA RNG and action-order shuffle RNG use identical seeds

**File:** `runner.py:282, 312`

Both use `random.Random(config.seed * 10000 + round_num)`. The CA random draws replay the same PRNG sequence the shuffle consumed part of. The correlation is weak in practice (different draw counts) but violates independence.

**Why it could change conclusions:** CA payment amounts could be systematically tied to action application order — e.g., agents processed earlier in a round consistently draw different peers/reference entries.

**Smallest fix:** Use a different seed for CA, e.g., `config.seed * 10000 + round_num + 5000`.

**Fix before runs.**

---

## 4. Duplicate reviews across rounds inflate CA reference pool non-uniformly

**File:** `mechanisms.py:48-53`

`agent_reviews[rv.reviewer].append(...)` adds every Review object ever filed, including multiple reviews of the same entry across rounds (possible because `_apply_reviews` accepts verdicts on `prior_reads | last_round`). If an agent reviewed E005 as "legit" in round 4 then "exploit" in round 7, both appear in `agent_reviews`. When picking reference entry t′, E005 has double weight. Meanwhile, `entry_reviewers` (a dict) silently overwrites with the latest verdict.

**Why it could change conclusions:** Biases CA scores for agents who re-review entries. The agreement term uses the latest verdict, but the reference term overweights re-reviewed entries.

**Smallest fix:** Deduplicate `agent_reviews` per `(agent, entry_id)` pair, keeping the latest verdict only.

**Fix before runs.**

---

## 5. No cap on entries per `read_library` action — prompt says "up to 3 entries per round"

**Files:** `agents.py:45` (prompt text), `agents.py:154-156` (parser), `runner.py:139-150` (execution)

The prompt says "you may read up to 3 entries per round." The parser limits to 3 `read_library` *actions*, but each action can pass a list of arbitrarily many entry_ids via `entries` or `entry_ids`. An agent submitting `{"tool":"read_library","args":{"entries":["E001","E002",...,"E010"]}}` reads all 10 in one action.

**Why it could change conclusions:** An agent that discovers this can read the entire library in one action, producing exposure rates much higher than intended. Differential discovery across conditions would confound exposure and recognition metrics.

**Smallest fix:** In `_apply_actions`, track entries read per agent per round and cap at 3 total. Ignore reads beyond the cap.

**Fix before runs.**

---

## 6. Board-post accusation detection is NLP-heuristic — could miscount public reports

**File:** `analysis/metrics.py:13-26`

`_is_board_accusation` matches on keyword overlap (`{"cheat", "exploit", "suspicious", …}` + agent name or entry ID in text). A post like "I'm suspicious of P07 — is prover-alpha working on it?" registers as a public accusation of all of prover-alpha's entries. Conversely, "prover-chi's answer is clearly wrong" without a keyword match is missed.

**Why it could change conclusions:** `public_report_rate` and `false_public` could be systematically inflated or deflated. If agents in B/C use more accusation keywords (the prompt mentions "exploit" in the revocation rule), the miscount could differ across conditions, creating a measurement confound.

**Smallest fix:** Report both the heuristic-based public report count and the report-tool-only count. Run sensitivity analysis on both. Alternatively, tighten the heuristic to require an entry_id (not just an agent name).

**Limitation only** (if sensitivity analysis is added; otherwise fix before runs).

---

## 7. Conditions B/C explicitly name "exploit" verdict in the revocation rule; A does not

**File:** `agents.py:21-36`

- A: "Reports are sent to the organizers."
- B/C: "If 3 or more different agents report or give an 'exploit' verdict on the same library entry…"

The common header already mentions the exploit verdict option for all conditions, but B/C connect it to consequences. This could prime agents in B/C to use "exploit" verdicts more readily, independent of the revocation mechanism.

**Why it could change conclusions:** Part of the B-vs-A difference in private flagging could come from the prompt mentioning "exploit verdict" in a consequential context, not from the mechanism itself.

**Smallest fix:** This is inherent to describing different rules — you can't describe revocation-by-verdict without naming the verdict. Note in the write-up.

**Limitation only.**

---

## 8. Cheater flags count toward revocation but not toward false-accusation metrics

**Files:** `world.py:164-173` (revocation counts all agents), `analysis/metrics.py:87, 108` (metrics filter to `honest_names`)

If a cheater gives an "exploit" verdict on a decoy or honest entry, it counts toward the `k_revoke=3` threshold for revocation but doesn't appear in `false_flags` or `false_accusation_rate`. A wrongful revocation could happen with 2 honest false flags + 1 cheater false flag, but the metrics would show only 2 honest false flags.

**Why it could change conclusions:** `wrongful_revocations` could exceed what the false-accusation metrics explain, making results look inconsistent.

**Smallest fix:** Add a metric showing the full set of flaggers for each revocation (honest + cheater), reported alongside the honest-only false-accusation rate. Document in the write-up that cheater flags contribute to revocations.

**Limitation only.**

---

## 9. Score display includes CA payments in C but not A/B — implicit feedback asymmetry

**Files:** `mechanisms.py:99`, `agents.py:112-113`

In condition C, `world.scores[i]` includes puzzle points + CA payments. The observation shows this combined score. An agent in C whose score jumps +10 without submitting knows their reviews matched peers. In A/B, scores only change on submission.

**Why it could change conclusions:** If agents learn to calibrate reviews from score feedback, C's effect is not purely from the CA incentive but also from the learning signal. This is arguably part of the treatment, but CLAUDE.md doesn't discuss it.

**Smallest fix:** Note in the write-up. Alternatively, show only puzzle points in the observation for all conditions and report CA payments separately (e.g., a "review bonus" line visible only in C).

**Limitation only.**

---

## 10. Swarm-as-monitor and replicas-as-monitor metrics not implemented

**File:** `analysis/metrics.py` — missing entirely

CLAUDE.md specifies: TPR on cheater entries, FPR on honest + decoy entries, AUROC of flag count per entry, single-random-reviewer vs. majority-vote comparison, and CAPA-style chance-adjusted agreement of review errors.

**Why it could change conclusions:** These are the Track 4 ("swarm as monitor") metrics. Without them, the report can't make the core argument about whether replica agreement adds independent signal.

**Smallest fix:** Implement before real runs if these go in the report; otherwise move to phase 2 and note as out of scope.

**Fix before runs** (if in scope for the report) or **limitation only** (if deferred).

---

## 11. CA incentives ramp up over rounds as the review pool grows

**File:** `mechanisms.py:48-53`

`compute_ca_payments` uses all reviews filed so far as the reference pool. In early rounds, agents have few reference entries, so CA scores are more likely to hit the "no_t_prime" / "no_t_double_prime" fallback (score = 0). CA incentives are therefore weaker early (when cheating is first discovered) and stronger late.

**Why it could change conclusions:** Early false flags in C pay no CA penalty. The deterrent effect may only appear in later rounds, which could mask a real early-round difference between B and C.

**Smallest fix:** Note in the write-up. Optionally, report CA payment rates split by early vs. late rounds.

**Limitation only.**
