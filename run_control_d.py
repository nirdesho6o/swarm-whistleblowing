"""Launch condition D control runs: seeds 0–9, 20 rounds, qwen3.5-397b.

Max 3 concurrent. Retries each crash once.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from swarm.config import Condition, RunConfig
from swarm.runner import run

MODEL = "qwen3.5-397b"
SEEDS = list(range(10))
ROUNDS = 20
MAX_CONCURRENT = 3


async def run_one(seed: int) -> dict:
    tag = f"D_seed{seed}"
    run_dir = Path(f"runs/control/{tag}")
    config = RunConfig(
        model=MODEL,
        condition=Condition.D,
        rounds=ROUNDS,
        seed=seed,
        n_agents=8,
        max_output_tokens=1500,
        temperature=0.7,
        semaphore_limit=8,
    )
    t0 = time.monotonic()
    try:
        result_dir = await run(config, run_dir)
        elapsed = time.monotonic() - t0
        credits = 0.0
        evpath = result_dir / "events.jsonl"
        if evpath.exists():
            for line in open(evpath):
                ev = json.loads(line)
                if ev["type"] == "run_summary":
                    credits = ev["payload"].get("total_credits", 0.0)
        return {"tag": tag, "ok": True, "credits": credits, "elapsed": elapsed}
    except Exception as e:
        elapsed = time.monotonic() - t0
        return {"tag": tag, "ok": False, "error": str(e)[:200], "elapsed": elapsed, "credits": 0.0}


async def main():
    total_credits = 0.0
    total_done = 0
    crashes = []
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def guarded(seed: int) -> dict:
        async with sem:
            return await run_one(seed)

    # Launch all seeds with semaphore limiting concurrency
    tasks = [guarded(s) for s in SEEDS]
    results = await asyncio.gather(*tasks)

    for r in results:
        if r["ok"]:
            total_done += 1
            total_credits += r["credits"]
            print(f"  OK {r['tag']}: {r['elapsed']:.0f}s, {r['credits']:.4f} credits")
        else:
            print(f"  CRASHED {r['tag']}: {r['error']}")
            # Retry once
            seed = int(r["tag"].split("seed")[1])
            print(f"    Retrying {r['tag']}...")
            retry = await run_one(seed)
            if retry["ok"]:
                total_done += 1
                total_credits += retry["credits"]
                print(f"    Retry OK: {retry['elapsed']:.0f}s, {retry['credits']:.4f} credits")
            else:
                crashes.append(r["tag"])
                print(f"    Retry FAILED: {retry.get('error', '')}")

    print(f"\nDone: {total_done}/10, credits: {total_credits:.4f}, crashes: {crashes}")
    if crashes:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
