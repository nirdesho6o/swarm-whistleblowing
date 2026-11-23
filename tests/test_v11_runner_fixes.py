"""v1.1 runner fixes: malformed action args no longer crash a run; decoy board-line state is per run."""
import json
from pathlib import Path

from swarm import runner
from swarm.agents import ParsedResponse
from swarm.config import Condition, RunConfig
from swarm.logging import EventLogger
from swarm.puzzles import make_puzzle_bank
from swarm.world import WorldState


def _world(tmp_path: Path, name: str, seed: int = 0, cond: str = "B") -> WorldState:
    cfg = RunConfig(model="test", condition=Condition(cond), rounds=20, seed=seed)
    return WorldState(config=cfg, puzzles=make_puzzle_bank(), logger=EventLogger(tmp_path / name, name))


def test_list_args_is_logged_invalid_not_a_crash(tmp_path):
    w = _world(tmp_path, "w")
    parsed = ParsedResponse(actions=[
        {"tool": "read_library", "args": []},
        {"tool": "submit", "args": "P01 2"},
        {"tool": "pass", "args": None},
    ])
    runner._apply_actions("prover-alpha", parsed, w, 0, {})
    w.logger.close()
    ev = [json.loads(l) for l in open(tmp_path / "w" / "events.jsonl")]
    inval = [e for e in ev if e["type"] == "action_invalid"]
    assert [e["payload"]["reason"] for e in inval] == ["args not an object", "args not an object"]
    assert any(e["type"] == "action" and e["payload"]["tool"] == "pass" for e in ev)


def _trace(w):
    return [(b.agent, b.text, b.round_posted) for b in w.board]


def test_decoy_board_state_isolated_between_interleaved_runs(tmp_path):
    alone = _world(tmp_path, "alone", seed=3)
    for r in range(20):
        runner._seed_agent_actions(alone, r)

    a = _world(tmp_path, "a", seed=3)
    b = _world(tmp_path, "b", seed=7)
    for r in range(20):  # interleave two runs round by round, as concurrent runs in one process do
        runner._seed_agent_actions(a, r)
        runner._seed_agent_actions(b, r)
    assert _trace(a) == _trace(alone)
    assert a.decoy_line_history is not b.decoy_line_history
