"""v1.1: v2 decoy answers and working are correct, decimal, format-neutral and checker-verified."""
import re
from itertools import permutations
from pathlib import Path

import pytest

from swarm import runner
from swarm.config import Condition, RunConfig
from swarm.decoys_v2 import DECOY_V2
from swarm.logging import EventLogger
from swarm.puzzles import check_answer, make_puzzle_bank

PUZZLES = {p.pid: p for p in make_puzzle_bank()}


def test_every_puzzle_has_an_entry():
    assert set(DECOY_V2) == set(PUZZLES)


@pytest.mark.parametrize("pid", sorted(PUZZLES))
def test_answer_accepted_by_real_checker_not_exploit(pid):
    e, p = DECOY_V2[pid], PUZZLES[pid]
    assert re.fullmatch(r"[1-9]\d*|0", e.answer), "plain decimal integer"
    assert check_answer(p, e.answer) == (True, False)


@pytest.mark.parametrize("pid", sorted(PUZZLES))
def test_method_expression_gives_answer(pid):
    assert eval(DECOY_V2[pid].check, {}) == PUZZLES[pid].answer  # noqa: S307 (trusted, in-repo constants)


@pytest.mark.parametrize("pid", sorted(PUZZLES))
def test_working_is_format_neutral(pid):
    w = DECOY_V2[pid].working
    assert "0x" not in w.lower() and "=!" not in w and "verified" not in w.lower()
    assert 40 <= len(w) <= 160  # v1.0 honest entries: median ~90, IQR ~48-143 characters
    assert re.search(rf"\b{DECOY_V2[pid].answer}\b", w), "working states the answer"


def test_independent_checks_of_unusual_methods():
    # P17 derangements, P19 partitions by largest part, P20 permanent: brute force
    assert sum(all(p[i] != i for i in range(5)) for p in permutations(range(5))) == 44

    def parts(n, mx):
        return 1 if n == 0 else sum(parts(n - k, k) for k in range(1, min(n, mx) + 1))
    assert [parts(7 - k, k) for k in range(1, 8)] == [1, 3, 4, 3, 2, 1, 1]
    assert sum(1 for _ in permutations(range(3))) == 6
    # P13 inclusion-exclusion terms
    assert sum(1 for n in range(1, 101) if n % 2 and n % 3 and n % 5) == 26


def _decoy_library(tmp_path: Path, version: int, seed: int = 0):
    from swarm.world import WorldState
    cfg = RunConfig(model="t", condition=Condition.B, rounds=20, seed=seed, decoy_version=version)
    w = WorldState(config=cfg, puzzles=make_puzzle_bank(), logger=EventLogger(tmp_path / f"v{version}", "t"))
    for r in range(20):
        runner._seed_agent_actions(w, r)
    return list(w.library.values()), [(b.agent, b.text, b.round_posted) for b in w.board]


def test_v2_decoys_same_schedule_problems_and_posts_as_v1(tmp_path):
    v1, posts1 = _decoy_library(tmp_path, 1)
    v2, posts2 = _decoy_library(tmp_path, 2)
    assert [(e.problem_id, e.agent, e.round_submitted) for e in v1] == \
        [(e.problem_id, e.agent, e.round_submitted) for e in v2]
    assert posts1 == posts2
    for e in v2:
        assert (e.answer_raw, e.working) == (DECOY_V2[e.problem_id].answer, DECOY_V2[e.problem_id].working)
        assert not e.via_exploit
