"""v1.2 Phase 1.5 launcher (PREREG_v1.2.md). REAL RUNS.

One Adaption queue, 3 runs at a time (as in v1.0/v1.1), in the pre-registered order:
  group 1: qwen3.5-397b B-odd-v1, B-odd-v2, B-stealth-v1, B-stealth-v2, interleaved by seed (seed 0 of all four
           cells, then seed 1, ...), seeds 0-19;
  group 2: glm-5.2 B, C, E, interleaved the same way, seeds 0-19.
All cells use v1.0 settings (temperature 0.7, max output tokens 1500, semaphore 8, 20 rounds, 8 LLM agents).

Safety (as in run_v11_phase1.py):
- Refuses to start unless PREREG_v1.2.md is committed and the working tree is clean (`--plan` only prints).
- Re-executes itself under `systemd-inhibit` (sleep, idle, lid switch) so the machine stays awake.
- Resumable: a run with a run_summary is complete and skipped; a run directory without one is moved to
  runs/v1.2/phase15/_incomplete/ and redone with the same seed (noted in the progress log and launcher_meta.json).
- A crashed run is retried once (same seed); a second crash marks it failed and the queue moves on.
- Stops launching new runs after 2026-11-27 23:59 IST (runs already started finish).
- The git hash is logged in every run (run_meta) and in launcher_meta.json.

Progress: runs/v1.2/phase15/progress.json and progress.log.
Usage:  python run_v12_phase15.py --plan     # show queue and status, no runs
        python run_v12_phase15.py            # start (after PREREG_v1.2.md is committed)
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "runs/v1.2/phase15"
PREREG = "PREREG_v1.2.md"
IST = ZoneInfo("Asia/Kolkata")
DEADLINE = dt.datetime(2026, 11, 27, 23, 59, tzinfo=IST)
PARALLEL = 3
QWEN, GLM = "qwen3.5-397b", "glm-5.2"
S0_19 = list(range(20))


@dataclass(frozen=True)
class Job:
    group: int
    cell: str           # e.g. "B-stealth-v1"
    model: str
    condition: str      # swarm.config.Condition value
    decoy_version: int
    exploit: str        # "odd" | "stealth"
    seed: int

    @property
    def name(self) -> str:
        return f"{self.cell}_seed{self.seed}"

    @property
    def model_dir(self) -> str:
        return self.model.replace(":", "__")

    def run_dir(self, out: Path = OUT) -> Path:
        return out / self.model_dir / self.name


# (group, model, [(cell, condition, decoy_version, exploit)], seeds)
PLAN = [
    (1, QWEN, [("B-odd-v1", "B", 1, "odd"), ("B-odd-v2", "B", 2, "odd"),
               ("B-stealth-v1", "B", 1, "stealth"), ("B-stealth-v2", "B", 2, "stealth")], S0_19),
    (2, GLM, [("B", "B", 1, "odd"), ("C", "C", 1, "odd"), ("E", "E", 1, "odd")], S0_19),
]


def build_queue(plan=PLAN) -> list[Job]:
    """Groups in order; within a group, seed by seed across all cells."""
    jobs = []
    for group, model, cells, seeds in sorted(plan, key=lambda g: g[0]):
        for seed in seeds:
            for cell, cond, dv, exploit in cells:
                jobs.append(Job(group, cell, model, cond, dv, exploit, seed))
    return jobs


def _summary_line(ev: Path) -> str | None:
    if not ev.exists():
        return None
    with open(ev, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 65536))
        tail = f.read().decode(errors="replace")
    for line in tail.splitlines():
        if '"type": "run_summary"' in line:
            return line
    return None


def run_status(job: Job, out: Path = OUT) -> str:
    if not job.run_dir(out).exists():
        return "todo"
    return "done" if _summary_line(job.run_dir(out) / "events.jsonl") else "incomplete"


def past_deadline(now: dt.datetime | None = None) -> bool:
    return (now or dt.datetime.now(IST)) > DEADLINE


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()


def preflight_errors() -> list[str]:
    errs = []
    try:
        git("ls-files", "--error-unmatch", PREREG)
    except subprocess.CalledProcessError:
        errs.append(f"{PREREG} is not committed (not tracked by git).")
    dirty = git("status", "--porcelain")
    if dirty:
        errs.append("Working tree is not clean:\n" + dirty)
    if not os.environ.get("ADAPTION_API_KEY"):
        errs.append("ADAPTION_API_KEY is not set.")
    return errs


class Progress:
    def __init__(self, out: Path, jobs: list[Job]):
        self.out, self.jobs = out, jobs
        self.running: dict[str, dict] = {}
        self.failed: dict[str, str] = {}
        self.notes: list[str] = []
        self.stop_reason = ""
        self.started = dt.datetime.now(IST).isoformat(timespec="seconds")
        out.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        line = f"{dt.datetime.now(IST).isoformat(timespec='seconds')}  {msg}"
        print(line, flush=True)
        with open(self.out / "progress.log", "a") as f:
            f.write(line + "\n")

    def write(self) -> None:
        groups: dict[str, dict] = {}
        for j in self.jobs:
            g = groups.setdefault(f"{j.group}: {j.model} {j.cell}", {"done": 0, "total": 0})
            g["total"] += 1
            g["done"] += run_status(j, self.out) == "done"
        state = {"updated": dt.datetime.now(IST).isoformat(timespec="seconds"), "launcher_started": self.started,
                 "git_hash": git("rev-parse", "HEAD"), "deadline": DEADLINE.isoformat(),
                 "past_deadline": past_deadline(), "running": self.running, "failed": self.failed,
                 "stopped": self.stop_reason, "groups": groups, "notes": self.notes[-50:]}
        tmp = self.out / "progress.json.tmp"
        tmp.write_text(json.dumps(state, indent=1))
        tmp.replace(self.out / "progress.json")


def quarantine_incomplete(job: Job, out: Path = OUT) -> Path:
    dest_root = out / "_incomplete"
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(IST).strftime("%Y%m%dT%H%M%S")
    dest = dest_root / f"{job.model_dir}__{job.name}__{stamp}"
    shutil.move(str(job.run_dir(out)), str(dest))
    return dest


async def run_job(job: Job, prog: Progress, attempt_note: str) -> bool:
    from swarm.config import Condition, RunConfig
    from swarm.runner import run

    cfg = RunConfig(model=job.model, condition=Condition(job.condition), rounds=20, seed=job.seed, n_agents=8,
                    max_output_tokens=1500, temperature=0.7, semaphore_limit=8,
                    decoy_version=job.decoy_version, exploit=job.exploit)
    d = job.run_dir(prog.out)
    d.mkdir(parents=True, exist_ok=True)
    meta = {"job": asdict(job), "git_hash": git("rev-parse", "HEAD"),
            "started": dt.datetime.now(IST).isoformat(timespec="seconds"), "note": attempt_note,
            "settings": "v1.0: temperature 0.7, max output tokens 1500, semaphore 8"}
    (d / "launcher_meta.json").write_text(json.dumps(meta, indent=1))
    t0 = time.monotonic()
    try:
        await run(cfg, d)
        prog.log(f"DONE   {job.model_dir}/{job.name} in {(time.monotonic() - t0) / 60:.1f} min")
        return True
    except Exception as e:
        prog.log(f"CRASH  {job.model_dir}/{job.name}: {str(e)[:200]}")
        return False


async def worker(jobs: list[Job], parallel: int, prog: Progress) -> None:
    sem = asyncio.Semaphore(parallel)
    pending = list(jobs)
    tasks: set[asyncio.Task] = set()

    async def one(job: Job):
        key = f"{job.model_dir}/{job.name}"
        note = ""
        if run_status(job, prog.out) == "incomplete":
            dest = quarantine_incomplete(job, prog.out)
            note = f"re-run after interrupted attempt (moved to {dest.relative_to(prog.out)})"
            prog.log(f"RERUN  {key}: {note}")
            prog.notes.append(f"{key}: {note}")
        prog.running[key] = {"since": dt.datetime.now(IST).isoformat(timespec="seconds"), "note": note}
        prog.write()
        ok = await run_job(job, prog, note)
        if not ok:
            dest = quarantine_incomplete(job, prog.out)
            retry_note = f"retry after crash (crashed attempt moved to {dest.relative_to(prog.out)})"
            prog.log(f"RETRY  {key}: {retry_note}")
            prog.notes.append(f"{key}: {retry_note}")
            ok = await run_job(job, prog, retry_note)
            if not ok:
                quarantine_incomplete(job, prog.out)
                prog.failed[key] = "crashed twice"
        prog.running.pop(key, None)
        prog.write()

    while pending:
        if past_deadline():
            prog.stop_reason = f"deadline {DEADLINE.isoformat()} passed; {len(pending)} runs not started"
            prog.log(f"STOP   {prog.stop_reason}")
            break
        job = pending[0]
        if run_status(job, prog.out) == "done":
            pending.pop(0)
            continue
        await sem.acquire()
        if past_deadline():
            sem.release()
            continue  # loop top records the stop
        pending.pop(0)

        async def guarded(j=job):
            try:
                await one(j)
            except Exception as e:  # never let one job's bookkeeping error kill the queue silently
                key = f"{j.model_dir}/{j.name}"
                prog.failed[key] = f"launcher error: {str(e)[:200]}"
                prog.running.pop(key, None)
                prog.log(f"ERROR  {key}: launcher error: {str(e)[:200]}")
                prog.write()
            finally:
                sem.release()
        t = asyncio.create_task(guarded())
        tasks.add(t)
        t.add_done_callback(tasks.discard)
    if tasks:
        await asyncio.gather(*tasks)
    prog.log("END    queue")
    prog.write()


def print_plan(jobs: list[Job], out: Path = OUT) -> None:
    print(f"{'#':>4}  {'group':>5}  {'model':14s} {'run':22s} status")
    for i, j in enumerate(jobs):
        print(f"{i:4d}  {j.group:5d}  {j.model:14s} {j.name:22s} {run_status(j, out)}")
    done = sum(run_status(j, out) == "done" for j in jobs)
    print(f"\n{done}/{len(jobs)} done; {PARALLEL} at a time; launch deadline {DEADLINE.isoformat()}")


async def main_async() -> None:
    jobs = build_queue()
    prog = Progress(OUT, jobs)
    prog.log(f"START  git {git('rev-parse', 'HEAD')}; {len(jobs)} runs x{PARALLEL}")
    prog.write()
    await worker(jobs, PARALLEL, prog)
    prog.log("ALL ENDED")
    prog.write()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print queue and status; start nothing")
    ap.add_argument("--inhibited", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    if args.plan:
        print_plan(build_queue())
        errs = preflight_errors()
        print("\nPreflight:", "OK" if not errs else "WOULD REFUSE TO START:\n- " + "\n- ".join(errs))
        return
    errs = preflight_errors()
    if errs:
        sys.exit("Refusing to start:\n- " + "\n- ".join(errs))
    if past_deadline():
        sys.exit(f"Refusing to start: past the launch deadline {DEADLINE.isoformat()}.")
    if not args.inhibited:
        cmd = ["systemd-inhibit", "--what=sleep:idle:handle-lid-switch", "--who=swarm-phase15",
               "--why=v1.2 Phase 1.5 real runs", "--mode=block",
               sys.executable, str(Path(__file__).resolve()), "--inhibited"]
        os.chdir(ROOT)
        os.execvp(cmd[0], cmd)
    os.chdir(ROOT)
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
