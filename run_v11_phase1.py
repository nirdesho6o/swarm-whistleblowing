"""v1.1 Phase 1 launcher (PREREG_v1.1.md). REAL RUNS.

Two queues run at the same time:
- Adaption queue (3 runs at a time, as in v1.0), in pre-registered priority order:
    (1) Qwen B, C  (2) Qwen E, E-CA  (3) Qwen B-v2, C-v2, D-v2  (4) glm-5.2 B, C, D
    (5) Qwen A seeds 10-19  (6) Qwen B-ask
  Seed by seed within each priority level, so a partly finished level still has complete paired seeds.
- Muse queue (meta:muse-spark-1.3, secondary third family; 2 at a time by default): B, C, D, seeds 0-19,
  native settings (temperature not sent = Meta default 1.0; reasoning_effort "minimal"; semaphore 4).
  Stops launching once Muse spend (USD, list price) would reach the $50 cap.

Safety:
- Refuses to start unless PREREG_v1.1.md is committed and the working tree is clean (`--plan` only prints).
- Re-executes itself under `systemd-inhibit` (sleep, idle, lid switch) so the machine stays awake.
- Resumable: a run whose events.jsonl has a run_summary is complete and skipped. A run directory without
  one (interrupted or crashed) is moved to runs/v1.1/phase1/_incomplete/ and the run is redone with the
  same seed; this is written to the progress log and to the new run's launcher_meta.json.
- A run that crashes is retried once (same seed); a second crash marks it failed and the queue moves on.
- Stops launching new runs after 2026-11-26 23:59 IST (runs already started finish).
- The git hash is logged in every run (run_meta, by swarm.runner) and in launcher_meta.json.

Progress: runs/v1.1/phase1/progress.json (current state) and progress.log (append-only history).
Usage:  python run_v11_phase1.py --plan     # show queue and status, no runs
        python run_v11_phase1.py            # start (after PREREG_v1.1.md is committed)
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
OUT = ROOT / "runs/v1.1/phase1"
IST = ZoneInfo("Asia/Kolkata")
DEADLINE = dt.datetime(2026, 11, 26, 23, 59, tzinfo=IST)
ADAPTION_PARALLEL = 3
MUSE_PARALLEL_DEFAULT = 2
MUSE_BUDGET_USD = 50.0
MUSE_COST_GUESS_USD = 1.0  # per in-flight run, until real per-run costs are known (gate run: $0.28)
QWEN, GLM, MUSE = "qwen3.5-397b", "glm-5.2", "meta:muse-spark-1.3"
S0_19 = list(range(20))


@dataclass(frozen=True)
class Job:
    queue: str          # "adaption" | "muse"
    group: int          # priority level (muse jobs: 0)
    setup: str          # e.g. "B", "E-CA", "B-v2"
    model: str
    condition: str      # swarm.config.Condition value
    decoy_version: int
    seed: int
    native: bool = False  # Muse: provider-native settings

    @property
    def name(self) -> str:
        return f"{self.setup}_seed{self.seed}"

    @property
    def model_dir(self) -> str:
        return self.model.replace(":", "__")

    def run_dir(self, out: Path = OUT) -> Path:
        return out / self.model_dir / self.name


# (group, model, [(setup, condition, decoy_version)], seeds)
ADAPTION_PLAN = [
    (1, QWEN, [("B", "B", 1), ("C", "C", 1)], S0_19),
    (2, QWEN, [("E", "E", 1), ("E-CA", "E-CA", 1)], S0_19),
    (3, QWEN, [("B-v2", "B", 2), ("C-v2", "C", 2), ("D-v2", "D", 2)], S0_19),
    (4, GLM, [("B", "B", 1), ("C", "C", 1), ("D", "D", 1)], S0_19),
    (5, QWEN, [("A", "A", 1)], list(range(10, 20))),
    (6, QWEN, [("B-ask", "B-ask", 1)], S0_19),
]
MUSE_PLAN = [(0, MUSE, [("B", "B", 1), ("C", "C", 1), ("D", "D", 1)], S0_19)]


def build_queue(plan, queue: str, native: bool = False) -> list[Job]:
    """Seed by seed within each priority level; levels in order."""
    jobs = []
    for group, model, setups, seeds in sorted(plan, key=lambda g: g[0]):
        for seed in seeds:
            for setup, cond, dv in setups:
                jobs.append(Job(queue, group, setup, model, cond, dv, seed, native))
    return jobs


def _summary_line(ev: Path) -> str | None:
    """The run_summary line, if present. It is written last, so only the file's tail is read."""
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
    """'done' (has run_summary), 'incomplete' (dir exists, no summary), or 'todo'."""
    if not job.run_dir(out).exists():
        return "todo"
    return "done" if _summary_line(job.run_dir(out) / "events.jsonl") else "incomplete"


def run_cost(job: Job, out: Path = OUT) -> float:
    line = _summary_line(job.run_dir(out) / "events.jsonl")
    return float(json.loads(line)["payload"].get("total_credits", 0.0)) if line else 0.0


def past_deadline(now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now(IST)
    return now > DEADLINE


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()


def preflight_errors() -> list[str]:
    errs = []
    try:
        git("ls-files", "--error-unmatch", "PREREG_v1.1.md")
    except subprocess.CalledProcessError:
        errs.append("PREREG_v1.1.md is not committed (not tracked by git).")
    dirty = git("status", "--porcelain")
    if dirty:
        errs.append("Working tree is not clean:\n" + dirty)
    for var in ("ADAPTION_API_KEY", "META_API_KEY"):
        if not os.environ.get(var):
            errs.append(f"{var} is not set.")
    return errs


class Progress:
    def __init__(self, out: Path, adaption: list[Job], muse: list[Job]):
        self.out = out
        self.jobs = {"adaption": adaption, "muse": muse}
        self.running: dict[str, dict] = {}
        self.failed: dict[str, str] = {}
        self.notes: list[str] = []
        self.started = dt.datetime.now(IST).isoformat(timespec="seconds")
        self.stop_reason: dict[str, str] = {}
        out.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str) -> None:
        line = f"{dt.datetime.now(IST).isoformat(timespec='seconds')}  {msg}"
        print(line, flush=True)
        with open(self.out / "progress.log", "a") as f:
            f.write(line + "\n")

    def write(self) -> None:
        def key(j):
            return f"{j.model_dir}/{j.name}"
        summary = {}
        for q, jobs in self.jobs.items():
            groups: dict[str, dict] = {}
            for j in jobs:
                g = groups.setdefault(f"{j.group}: {j.model} {j.setup}", {"done": 0, "total": 0})
                g["total"] += 1
                g["done"] += run_status(j, self.out) == "done"
            summary[q] = groups
        muse_spend = sum(run_cost(j, self.out) for j in self.jobs["muse"] if run_status(j, self.out) == "done")
        state = {
            "updated": dt.datetime.now(IST).isoformat(timespec="seconds"),
            "launcher_started": self.started,
            "git_hash": git("rev-parse", "HEAD"),
            "deadline": DEADLINE.isoformat(),
            "past_deadline": past_deadline(),
            "running": self.running,
            "failed": self.failed,
            "stopped": self.stop_reason,
            "muse_spend_usd": round(muse_spend, 4),
            "muse_budget_usd": MUSE_BUDGET_USD,
            "groups": summary,
            "notes": self.notes[-50:],
        }
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

    cfg = RunConfig(
        model=job.model, condition=Condition(job.condition), rounds=20, seed=job.seed, n_agents=8,
        max_output_tokens=1500, temperature=None if job.native else 0.7,
        semaphore_limit=4 if job.native else 8, decoy_version=job.decoy_version,
    )
    d = job.run_dir(prog.out)
    d.mkdir(parents=True, exist_ok=True)
    meta = {"job": asdict(job), "git_hash": git("rev-parse", "HEAD"),
            "started": dt.datetime.now(IST).isoformat(timespec="seconds"), "note": attempt_note,
            "settings": ("native: temperature not sent (Meta default 1.0), reasoning_effort=minimal, "
                         "semaphore 4" if job.native else "v1.0: temperature 0.7, semaphore 8")}
    (d / "launcher_meta.json").write_text(json.dumps(meta, indent=1))
    t0 = time.monotonic()
    try:
        await run(cfg, d)
        prog.log(f"DONE   {job.queue:8s} {job.model_dir}/{job.name} in {(time.monotonic() - t0) / 60:.1f} min")
        return True
    except Exception as e:
        prog.log(f"CRASH  {job.queue:8s} {job.model_dir}/{job.name}: {str(e)[:200]}")
        return False


async def worker(name: str, queue: list[Job], parallel: int, prog: Progress, budget_usd: float | None) -> None:
    sem = asyncio.Semaphore(parallel)
    pending = list(queue)
    tasks: set[asyncio.Task] = set()
    in_flight = 0

    async def one(job: Job):
        key = f"{job.model_dir}/{job.name}"
        note = ""
        st = run_status(job, prog.out)
        if st == "incomplete":
            dest = quarantine_incomplete(job, prog.out)
            note = f"re-run after interrupted attempt (moved to {dest.relative_to(prog.out)})"
            prog.log(f"RERUN  {key}: {note}")
            prog.notes.append(f"{key}: {note}")
        prog.running[key] = {"queue": name, "since": dt.datetime.now(IST).isoformat(timespec="seconds"),
                             "note": note}
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
            prog.stop_reason[name] = f"deadline {DEADLINE.isoformat()} passed; {len(pending)} runs not started"
            prog.log(f"STOP   {name}: {prog.stop_reason[name]}")
            break
        job = pending[0]
        if run_status(job, prog.out) == "done":
            pending.pop(0)
            continue
        await sem.acquire()
        if budget_usd is not None:
            spent = sum(run_cost(j, prog.out) for j in queue if run_status(j, prog.out) == "done")
            if spent + in_flight * MUSE_COST_GUESS_USD >= budget_usd:
                sem.release()
                prog.stop_reason[name] = (f"budget: spent ${spent:.2f} + {in_flight} in flight would reach "
                                          f"${budget_usd:.0f}; {len(pending)} runs not started")
                prog.log(f"STOP   {name}: {prog.stop_reason[name]}")
                break
        if past_deadline():
            sem.release()
            continue  # loop top records the stop
        pending.pop(0)
        in_flight += 1

        async def guarded(j=job):
            nonlocal in_flight
            try:
                await one(j)
            except Exception as e:  # never let one job's bookkeeping error kill the queue silently
                key = f"{j.model_dir}/{j.name}"
                prog.failed[key] = f"launcher error: {str(e)[:200]}"
                prog.running.pop(key, None)
                prog.log(f"ERROR  {key}: launcher error: {str(e)[:200]}")
                prog.write()
            finally:
                in_flight -= 1
                sem.release()
        t = asyncio.create_task(guarded())
        tasks.add(t)
        t.add_done_callback(tasks.discard)
    if tasks:
        await asyncio.gather(*tasks)
    prog.log(f"END    {name} queue")
    prog.write()


def print_plan(adaption: list[Job], muse: list[Job], out: Path = OUT) -> None:
    for label, jobs in (("Adaption queue (3 at a time)", adaption), ("Muse queue (secondary)", muse)):
        print(f"\n{label}: {len(jobs)} runs")
        seen = {}
        for j in jobs:
            k = (j.group, j.model, j.setup)
            s = seen.setdefault(k, {"todo": 0, "done": 0, "incomplete": 0, "seeds": []})
            s[run_status(j, out)] += 1
            s["seeds"].append(j.seed)
        for (g, m, setup), s in seen.items():
            print(f"  [{g}] {m:22s} {setup:6s} seeds {min(s['seeds'])}-{max(s['seeds'])}: "
                  f"done {s['done']}, incomplete {s['incomplete']}, todo {s['todo']}")
    print("\nFirst 8 Adaption launches:", [f"{j.model}/{j.name}" for j in adaption[:8]])
    print(f"Deadline for new launches: {DEADLINE.isoformat()} (past: {past_deadline()})")


async def main_async(args) -> None:
    adaption = build_queue(ADAPTION_PLAN, "adaption")
    muse = build_queue(MUSE_PLAN, "muse", native=True)
    prog = Progress(OUT, adaption, muse)
    prog.log(f"START  git {git('rev-parse', 'HEAD')}; adaption {len(adaption)} runs x{ADAPTION_PARALLEL}, "
             f"muse {len(muse)} runs x{args.muse_parallel}, Muse cap ${MUSE_BUDGET_USD:.0f}")
    prog.write()
    await asyncio.gather(
        worker("adaption", adaption, ADAPTION_PARALLEL, prog, None),
        worker("muse", muse, args.muse_parallel, prog, MUSE_BUDGET_USD),
    )
    prog.log("ALL QUEUES ENDED")
    prog.write()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print queue and status; start nothing")
    ap.add_argument("--muse-parallel", type=int, default=MUSE_PARALLEL_DEFAULT, choices=[2, 3])
    ap.add_argument("--inhibited", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    if args.plan:
        print_plan(build_queue(ADAPTION_PLAN, "adaption"), build_queue(MUSE_PLAN, "muse", native=True))
        errs = preflight_errors()
        print("\nPreflight:", "OK" if not errs else "WOULD REFUSE TO START:\n- " + "\n- ".join(errs))
        return

    errs = preflight_errors()
    if errs:
        sys.exit("Refusing to start:\n- " + "\n- ".join(errs))
    if past_deadline():
        sys.exit(f"Refusing to start: past the launch deadline {DEADLINE.isoformat()}.")

    if not args.inhibited:
        cmd = ["systemd-inhibit", "--what=sleep:idle:handle-lid-switch", "--who=swarm-phase1",
               "--why=v1.1 Phase 1 real runs", "--mode=block",
               sys.executable, str(Path(__file__).resolve()), "--inhibited", "--muse-parallel", str(args.muse_parallel)]
        os.chdir(ROOT)
        os.execvp(cmd[0], cmd)

    os.chdir(ROOT)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
