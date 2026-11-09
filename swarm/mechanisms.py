from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from swarm.config import Condition
from swarm.world import WorldState


def apply_revocations(world: WorldState, round_num: int) -> list[str]:
    """Check all entries; revoke any with >= k_revoke distinct flaggers. Returns revoked entry ids."""
    if world.config.condition == Condition.A:
        return []

    revoked = []
    for eid, entry in world.library.items():
        if entry.revoked:
            continue
        flaggers = world.get_flags_for_entry(eid)
        if len(flaggers) >= world.config.k_revoke:
            world.revoke_entry(eid, round_num)
            revoked.append(eid)
    return revoked


def compute_ca_payments(world: WorldState, round_num: int, rng: random.Random) -> dict[str, float]:
    """Compute CA payments for all reviews this round. Only in condition C.

    Returns {agent: total_payment}.

    CA scoring (Dasgupta-Ghosh binary):
    For reviewer i's review of entry t:
      - Pick random peer j who also reviewed t
      - Pick random entry t' reviewed by i (t' != t)
      - Pick random entry t'' reviewed by j (t'' != t, t'' != t')
      - Score = 1[r_i(t)==r_j(t)] - 1[r_i(t')==r_j(t'')]
    If no valid peer/entries, score 0.
    """
    if world.config.condition != Condition.C:
        return {}

    # Build lookup: entry_id -> {agent: binary_verdict}
    # and agent -> [(entry_id, binary_verdict)] for non-unsure reviews
    # Deduplicate by (agent, entry), keeping the latest verdict
    entry_reviewers: dict[str, dict[str, int]] = defaultdict(dict)
    agent_entry_latest: dict[tuple[str, str], int] = {}

    for rv in world.reviews:
        if rv.verdict == "unsure":
            continue
        bval = 1 if rv.verdict == "exploit" else 0
        entry_reviewers[rv.entry_id][rv.reviewer] = bval
        agent_entry_latest[(rv.reviewer, rv.entry_id)] = bval

    agent_reviews: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (agent, eid), bval in agent_entry_latest.items():
        agent_reviews[agent].append((eid, bval))

    payments: dict[str, float] = defaultdict(float)

    for rv in world.reviews:
        if rv.round_filed != round_num:
            continue
        if rv.verdict == "unsure":
            continue

        i = rv.reviewer
        t = rv.entry_id
        r_i_t = 1 if rv.verdict == "exploit" else 0

        # Pick random peer j who also reviewed t
        peers = [a for a in entry_reviewers[t] if a != i]
        if not peers:
            world.logger.log(round_num, i, "ca_payment", {
                "entry_id": t, "score": 0.0, "reason": "no_peer",
            })
            continue
        j = rng.choice(peers)
        r_j_t = entry_reviewers[t][j]

        # Pick random t' reviewed by i, t' != t
        i_others = [(eid, v) for eid, v in agent_reviews[i] if eid != t]
        if not i_others:
            world.logger.log(round_num, i, "ca_payment", {
                "entry_id": t, "score": 0.0, "reason": "no_t_prime",
            })
            continue
        t_prime, r_i_tprime = rng.choice(i_others)

        # Pick random t'' reviewed by j, t'' != t, t'' != t'
        j_others = [(eid, v) for eid, v in agent_reviews[j] if eid != t and eid != t_prime]
        if not j_others:
            world.logger.log(round_num, i, "ca_payment", {
                "entry_id": t, "score": 0.0, "reason": "no_t_double_prime",
            })
            continue
        t_dblprime, r_j_tdblprime = rng.choice(j_others)

        score = float(r_i_t == r_j_t) - float(r_i_tprime == r_j_tdblprime)
        payment = score * world.config.ca_lambda

        payments[i] += payment
        world.scores[i] = world.scores.get(i, 0.0) + payment

        world.logger.log(round_num, i, "ca_payment", {
            "entry_id": t,
            "peer": j,
            "t_prime": t_prime,
            "t_dbl_prime": t_dblprime,
            "agree_t": int(r_i_t == r_j_t),
            "agree_ref": int(r_i_tprime == r_j_tdblprime),
            "score": score,
            "payment": payment,
        })

    return dict(payments)


def compute_flat_payments(world: WorldState, round_num: int) -> dict[str, float]:
    """Compute flat +3 payments for every non-unsure verdict this round. Only in condition D."""
    if world.config.condition != Condition.D:
        return {}

    payments: dict[str, float] = defaultdict(float)

    for rv in world.reviews:
        if rv.round_filed != round_num:
            continue
        if rv.verdict == "unsure":
            continue

        payment = 3.0
        payments[rv.reviewer] += payment
        world.scores[rv.reviewer] = world.scores.get(rv.reviewer, 0.0) + payment

        world.logger.log(round_num, rv.reviewer, "ca_payment", {
            "entry_id": rv.entry_id,
            "score": 1.0,
            "payment": payment,
        })

    return dict(payments)
