"""v1.2 Phase 1.5 launcher: queue order, resume, retry, deadline, preflight, run settings. No API calls."""
import asyncio
import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase15", ROOT / "run_v12_phase15.py")
L = importlib.util.module_from_spec(spec)
sys.modules["phase15"] = L
spec.loader.exec_module(L)


@pytest.fixture(autouse=True)
def _no_git(monkeypatch):
    monkeypatch.setattr(L, "git", lambda *a: "deadbeef" if a[0] == "rev-parse" else "")


def _write_run(job, out, done):
    d = job.run_dir(out)
    d.mkdir(parents=True, exist_ok=True)
    lines = [{"type": "run_meta", "payload": {}}]
    if done:
        lines.append({"type": "run_summary", "payload": {"total_credits": 0.5}})
    (d / "events.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def test_queue_order_interleaved_by_seed_then_glm():
    q = L.build_queue()
    assert len(q) == 140
    first = [(j.seed, j.cell) for j in q[:8]]
    assert first == [(0, "B-odd-v1"), (0, "B-odd-v2"), (0, "B-stealth-v1"), (0, "B-stealth-v2"),
                     (1, "B-odd-v1"), (1, "B-odd-v2"), (1, "B-stealth-v1"), (1, "B-stealth-v2")]
    assert all(j.model == L.QWEN for j in q[:80]) and all(j.model == L.GLM for j in q[80:])
    assert [(j.seed, j.cell) for j in q[80:83]] == [(0, "B"), (0, "C"), (0, "E")]
    cells = {(j.cell, j.condition, j.decoy_version, j.exploit) for j in q if j.model == L.QWEN}
    assert cells == {("B-odd-v1", "B", 1, "odd"), ("B-odd-v2", "B", 2, "odd"),
                     ("B-stealth-v1", "B", 1, "stealth"), ("B-stealth-v2", "B", 2, "stealth")}
    assert {(j.cell, j.condition, j.exploit) for j in q if j.model == L.GLM} == {
        ("B", "B", "odd"), ("C", "C", "odd"), ("E", "E", "odd")}


def test_deadline_is_nov27_ist():
    assert not L.past_deadline(dt.datetime(2026, 11, 27, 23, 58, tzinfo=L.IST))
    assert L.past_deadline(dt.datetime(2026, 11, 28, 0, 0, tzinfo=L.IST))
    assert L.past_deadline(dt.datetime(2026, 11, 27, 18, 30, tzinfo=dt.timezone.utc))


def _fake(monkeypatch, crash_first=(), crash_always=()):
    calls = []

    async def fake_run_job(job, prog, note):
        key = f"{job.model_dir}/{job.name}"
        calls.append((key, note))
        if key in crash_always or (key in crash_first and sum(c[0] == key for c in calls) == 1):
            _write_run(job, prog.out, done=False)
            return False
        _write_run(job, prog.out, done=True)
        return True
    monkeypatch.setattr(L, "run_job", fake_run_job)
    return calls


def test_resume_retry_and_deadline(monkeypatch, tmp_path):
    jobs = L.build_queue()[:6]
    _write_run(jobs[0], tmp_path, done=True)
    _write_run(jobs[1], tmp_path, done=False)
    k = lambda j: f"{j.model_dir}/{j.name}"  # noqa: E731
    calls = _fake(monkeypatch, crash_first={k(jobs[2])}, crash_always={k(jobs[3])})
    prog = L.Progress(tmp_path, jobs)
    asyncio.run(L.worker(jobs, 3, prog))
    ran = [c[0] for c in calls]
    assert k(jobs[0]) not in ran
    assert dict(calls)[k(jobs[1])].startswith("re-run after interrupted attempt")
    assert ran.count(k(jobs[2])) == 2 and L.run_status(jobs[2], tmp_path) == "done"
    assert prog.failed == {k(jobs[3]): "crashed twice"}
    assert json.loads((tmp_path / "progress.json").read_text())["git_hash"] == "deadbeef"

    calls2 = _fake(monkeypatch)
    monkeypatch.setattr(L, "past_deadline", lambda now=None: True)
    prog2 = L.Progress(tmp_path / "x", jobs)
    asyncio.run(L.worker(jobs, 3, prog2))
    assert calls2 == [] and "deadline" in prog2.stop_reason


def test_preflight(monkeypatch):
    def fake_git(*a):
        if a[0] == "ls-files":
            raise subprocess.CalledProcessError(1, "git")
        return "?? PREREG_v1.2.md" if a[0] == "status" else "x"
    monkeypatch.setattr(L, "git", fake_git)
    monkeypatch.setenv("ADAPTION_API_KEY", "x")
    errs = L.preflight_errors()
    assert any("PREREG_v1.2.md is not committed" in e for e in errs) and any("not clean" in e for e in errs)
    monkeypatch.setattr(L, "git", lambda *a: "")
    assert L.preflight_errors() == []
    monkeypatch.delenv("ADAPTION_API_KEY")
    assert L.preflight_errors() == ["ADAPTION_API_KEY is not set."]


def test_run_job_passes_cell_settings(monkeypatch, tmp_path):
    seen = {}

    async def fake_run(cfg, d):
        seen["cfg"] = cfg
    import swarm.runner
    monkeypatch.setattr(swarm.runner, "run", fake_run)
    job = next(j for j in L.build_queue() if j.cell == "B-stealth-v2")
    prog = L.Progress(tmp_path, [job])
    assert asyncio.run(L.run_job(job, prog, ""))
    c = seen["cfg"]
    assert (c.exploit, c.decoy_version, c.condition.value, c.temperature, c.max_output_tokens, c.semaphore_limit,
            c.rounds, c.n_agents) == ("stealth", 2, "B", 0.7, 1500, 8, 20, 8)
    meta = json.loads((job.run_dir(tmp_path) / "launcher_meta.json").read_text())
    assert meta["job"]["exploit"] == "stealth" and meta["git_hash"] == "deadbeef"
