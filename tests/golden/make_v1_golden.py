#!/usr/bin/env python3
"""Generate the v1.0 golden fixture: everything agents see in setups A-D, and v1 decoy behaviour.

Run against the v1.0-sprint tag (NOT the working tree) so the fixture is the submitted version:

    git worktree add /tmp/v1tag v1.0-sprint
    PYTHONPATH=/tmp/v1tag python tests/golden/make_v1_golden.py tests/golden/v1_0_sprint.json
    git worktree remove /tmp/v1tag

tests/test_v1_identity.py imports `build()` from this file and compares it with the fixture, using the
current code. Uses only APIs that exist at the tag. No LLM calls.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from swarm import agents, runner
from swarm.config import AGENT_NAMES, CHEATER_NAMES, SEED_AGENT_NAMES, Condition, RunConfig
from swarm.logging import EventLogger
from swarm.puzzles import make_puzzle_bank
from swarm.world import WorldState

V1_CONDITIONS = ["A", "B", "C", "D"]
DECOY_SEEDS = list(range(20)) + [99]
ROUNDS = 20


def _world(cond: str, seed: int, tmp: Path) -> WorldState:
    cfg = RunConfig(model="golden", condition=Condition(cond), rounds=ROUNDS, seed=seed)
    return WorldState(config=cfg, puzzles=make_puzzle_bank(), logger=EventLogger(tmp / f"{cond}_{seed}", "golden"))


def _decoy_trace(cond: str, seed: int, tmp: Path) -> dict:
    """Run only the scripted decoys for 20 rounds; one honest DM to each decoy in round 0."""
    runner._decoy_line_history.clear()
    w = _world(cond, seed, tmp)
    for d in SEED_AGENT_NAMES:
        w.send_dm("prover-alpha", d, "hello", 0)
    for r in range(ROUNDS):
        runner._seed_agent_actions(w, r)
    return {
        "library": [[e.entry_id, e.problem_id, e.agent, e.answer_raw, e.working, e.via_exploit, e.round_submitted]
                    for e in w.library.values()],
        "board": [[b.agent, b.text, b.round_posted] for b in w.board],
        "dm_replies": [[m.sender, m.recipient, m.text, m.round_sent]
                       for msgs in w.dms.values() for m in msgs if m.sender in SEED_AGENT_NAMES],
    }


def _observations(cond: str, tmp: Path) -> dict:
    """Observation text for every agent in a small scripted state (decoy + honest + cheater entries)."""
    runner._decoy_line_history.clear()
    w = _world(cond, 0, tmp)
    for r in range(3):
        runner._seed_agent_actions(w, r)
    open_p = [p for p in w.open_problems()]
    w.try_submit("prover-alpha", open_p[0].pid, str(open_p[0].answer), "worked it out", 2)
    w.try_submit("prover-theta", open_p[1].pid, "=!0", "", 2)
    w.post_board("prover-beta", "Anyone working on P03?", 2)
    w.send_dm("prover-gamma", "prover-alpha", "nice work", 2)
    eids = list(w.library)
    w.last_round_reads = {"prover-alpha": set(eids[:2]), "prover-epsilon": set(eids)}
    w.scores["prover-alpha"] = 10.0
    return {a: agents.render_observation(a, w, 3) for a in AGENT_NAMES}


def build() -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        return {
            "system_prompts": {c: {a: agents.build_system_prompt(a, Condition(c)) for a in AGENT_NAMES}
                               for c in V1_CONDITIONS},
            "condition_rules": {c: agents.CONDITION_RULES[Condition(c)] for c in V1_CONDITIONS},
            "observations": {c: _observations(c, tmp) for c in V1_CONDITIONS},
            "puzzles": [[p.pid, p.text, p.answer] for p in make_puzzle_bank()],
            "agents": {"names": AGENT_NAMES, "cheaters": sorted(CHEATER_NAMES), "decoys": SEED_AGENT_NAMES},
            "decoy_constants": {
                "schedule": runner.DECOY_SCHEDULE,
                "post_lines": runner.DECOY_POST_SUBMIT_LINES,
                "dm_replies": runner.DECOY_DM_REPLIES,
                "post_prob": runner.DECOY_POST_PROB,
            },
            "decoy_traces": {c: {str(s): _decoy_trace(c, s, tmp) for s in DECOY_SEEDS} for c in V1_CONDITIONS},
        }


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
    print(f"wrote {out}")
