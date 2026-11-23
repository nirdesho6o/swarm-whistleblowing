"""v1.1 Phase 1 launcher: queue order, resume, retry, deadline, budget, preflight. No API calls."""
import asyncio
import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase1", ROOT / "run_v11_phase1.py")
L = importlib.util.module_from_spec(spec)
import sys  # noqa: E402
sys.modules["phase1"] = L
spec.loader.exec_module(L)


@pytest.fixture(autouse=True)
def _no_git(monkeypatch):
    monkeypatch.setattr(L, "git", lambda *a: "deadbeef" if a[0] == "rev-parse" else "")


def test_queue_sizes_and_priority_order():
    a = L.build_queue(L.ADAPTION_PLAN, "adaption")
    m = L.build_queue(L.MUSE_PLAN, "muse", native=True)
    assert len(a) == 20 * 2 + 20 * 2 + 20 * 3 + 20 * 3 + 10 + 20 == 230
    assert len(m) == 60 and all(j.native and j.model == "meta:muse-spark-1.3" for j in m)
    assert [j.group for j in a] == sorted(j.group for j in a)
    # seed by seed within a level
    g1 = [(j.seed, j.setup) for j in a if j.group == 1]
    assert g1[:4] == [(0, "B"), (0, "C"), (1, "B"), (1, "C")]
    g3 = [(j.setup, j.condition, j.decoy_version) for j in a if j.group == 3][:3]
    assert g3 == [("B-v2", "B", 2), ("C-v2", "C", 2), ("D-v2", "D", 2)]
    assert {j.seed for j in a if j.group == 5} == set(range(10, 20))
    assert {(j.model, j.setup) for j in a if j.group == 4} == {("glm-5.2", s) for s in "BCD"}


def _write_run(job, out, done=True, cost=0.5):
    d = job.run_dir(out)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "events.jsonl", "w") as f:
        f.write(json.dumps({"type": "run_meta", "payload": {}}) + "\n")
        if done:
            f.write(json.dumps({"type": "run_summary", "payload": {"total_credits": cost}}) + "\n")


def test_run_status(tmp_path):
    j = L.Job("adaption", 1, "B", "qwen3.5-397b", "B", 1, 0)
    assert L.run_status(j, tmp_path) == "todo"
    _write_run(j, tmp_path, done=False)
    assert L.run_status(j, tmp_path) == "incomplete"
    _write_run(j, tmp_path, done=True, cost=0.7)
    assert L.run_status(j, tmp_path) == "done" and L.run_cost(j, tmp_path) == 0.7


def test_deadline_is_ist():
    assert not L.past_deadline(dt.datetime(2026, 11, 26, 23, 58, tzinfo=L.IST))
    assert L.past_deadline(dt.datetime(2026, 11, 27, 0, 0, tzinfo=L.IST))
    # 18:30 UTC on Nov 26 = 00:00 IST Nov 27
    assert L.past_deadline(dt.datetime(2026, 11, 26, 18, 30, tzinfo=dt.timezone.utc))


def _fake_runner(monkeypatch, tmp_path, crash_first=(), crash_always=(), cost=0.5):
    calls = []

    async def fake_run_job(job, prog, note):
        calls.append((f"{job.model_dir}/{job.name}", note))
        key = f"{job.model_dir}/{job.name}"
        if key in crash_always or (key in crash_first and sum(c[0] == key for c in calls) == 1):
            _write_run(job, prog.out, done=False)
            return False
        _write_run(job, prog.out, done=True, cost=cost)
        return True

    monkeypatch.setattr(L, "run_job", fake_run_job)
    return calls


def test_resume_skips_done_and_reruns_incomplete_with_note(monkeypatch, tmp_path):
    jobs = L.build_queue([(1, "qwen3.5-397b", [("B", "B", 1), ("C", "C", 1)], [0, 1])], "adaption")
    _write_run(jobs[0], tmp_path, done=True)      # B_seed0 done
    _write_run(jobs[1], tmp_path, done=False)     # C_seed0 interrupted
    calls = _fake_runner(monkeypatch, tmp_path)
    prog = L.Progress(tmp_path, jobs, [])
    asyncio.run(L.worker("adaption", jobs, 3, prog, None))
    ran = [c[0] for c in calls]
    assert "qwen3.5-397b/B_seed0" not in ran
    assert set(ran) == {"qwen3.5-397b/C_seed0", "qwen3.5-397b/B_seed1", "qwen3.5-397b/C_seed1"}
    assert dict(calls)["qwen3.5-397b/C_seed0"].startswith("re-run after interrupted attempt")
    assert len(list((tmp_path / "_incomplete").iterdir())) == 1
    assert all(L.run_status(j, tmp_path) == "done" for j in jobs)
    state = json.loads((tmp_path / "progress.json").read_text())
    assert state["git_hash"] == "deadbeef" and state["groups"]["adaption"]["1: qwen3.5-397b C"]["done"] == 2
    assert "RERUN" in (tmp_path / "progress.log").read_text()


def test_crash_retried_once_then_marked_failed(monkeypatch, tmp_path):
    jobs = L.build_queue([(1, "qwen3.5-397b", [("B", "B", 1)], [0, 1, 2])], "adaption")
    calls = _fake_runner(monkeypatch, tmp_path, crash_first={"qwen3.5-397b/B_seed0"},
                         crash_always={"qwen3.5-397b/B_seed1"})
    prog = L.Progress(tmp_path, jobs, [])
    asyncio.run(L.worker("adaption", jobs, 1, prog, None))
    keys = [c[0] for c in calls]
    assert keys.count("qwen3.5-397b/B_seed0") == 2 and keys.count("qwen3.5-397b/B_seed1") == 2
    assert L.run_status(jobs[0], tmp_path) == "done"
    assert L.run_status(jobs[1], tmp_path) == "todo" and prog.failed == {"qwen3.5-397b/B_seed1": "crashed twice"}
    assert L.run_status(jobs[2], tmp_path) == "done"


def test_deadline_stops_new_launches(monkeypatch, tmp_path):
    jobs = L.build_queue([(1, "qwen3.5-397b", [("B", "B", 1)], [0, 1])], "adaption")
    calls = _fake_runner(monkeypatch, tmp_path)
    monkeypatch.setattr(L, "past_deadline", lambda now=None: True)
    prog = L.Progress(tmp_path, jobs, [])
    asyncio.run(L.worker("adaption", jobs, 3, prog, None))
    assert calls == [] and "deadline" in prog.stop_reason["adaption"]


def test_muse_budget_cap(monkeypatch, tmp_path):
    jobs = L.build_queue(L.MUSE_PLAN, "muse", native=True)[:10]
    calls = _fake_runner(monkeypatch, tmp_path, cost=20.0)
    prog = L.Progress(tmp_path, [], jobs)
    asyncio.run(L.worker("muse", jobs, 1, prog, 50.0))
    # $20 + $20 = $40; a third run would bring spend (40) + 1 in flight guess... checked before launch:
    # launch 1 (0+0<50), 2 (20<50), 3 (40<50) -> 60 spent; 4th refused
    assert len(calls) == 3 and "budget" in prog.stop_reason["muse"]


def test_preflight_refuses_untracked_prereg_and_dirty_tree(monkeypatch):
    import subprocess

    def fake_git(*a):
        if a[0] == "ls-files":
            raise subprocess.CalledProcessError(1, "git")
        if a[0] == "status":
            return "?? PREREG_v1.1.md"
        return "x"
    monkeypatch.setattr(L, "git", fake_git)
    monkeypatch.setenv("ADAPTION_API_KEY", "x")
    monkeypatch.setenv("META_API_KEY", "x")
    errs = L.preflight_errors()
    assert any("not committed" in e for e in errs) and any("not clean" in e for e in errs)

    monkeypatch.setattr(L, "git", lambda *a: "")
    assert L.preflight_errors() == []
