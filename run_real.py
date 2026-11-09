"""Launch all 30 real runs: conditions A/B/C × seeds 0–9, 20 rounds, qwen3.5-397b.

Batches by seed: runs A/B/C of the same seed together (3 concurrent).
Reduces concurrency if throttling detected. Retries each crash once.
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
CONDITIONS = [Condition.A, Condition.B, Condition.C]
ROUNDS = 20
MAX_CONCURRENT = 3


async def run_one(condition: Condition, seed: int) -> dict:
    """Run a single (condition, seed) and return status dict."""
    tag = f"{condition.value}_seed{seed}"
    run_dir = Path(f"runs/real/{tag}")
    config = RunConfig(
        model=MODEL,
        condition=condition,
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
        # Read credits from run_summary event
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
    retried_ok = []

    for seed in SEEDS:
        batch_label = f"Seed {seed}"
        print(f"\n{'='*60}")
        print(f"  {batch_label}: launching A, B, C in parallel")
        print(f"{'='*60}")

        tasks = [run_one(cond, seed) for cond in CONDITIONS]
        results = await asyncio.gather(*tasks)

        # Check for crashes, retry once
        for r in results:
            if r["ok"]:
                total_done += 1
                total_credits += r["credits"]
                print(f"  ✓ {r['tag']}: {r['elapsed']:.0f}s, {r['credits']:.4f} credits")
            else:
                print(f"  ✗ {r['tag']}: CRASHED — {r['error']}")
                # Parse condition and seed from tag
                parts = r["tag"].split("_seed")
                cond = Condition(parts[0])
                s = int(parts[1])
                print(f"    Retrying {r['tag']}...")
                retry = await run_one(cond, s)
                if retry["ok"]:
                    total_done += 1
                    total_credits += retry["credits"]
                    retried_ok.append(r["tag"])
                    print(f"    ✓ Retry OK: {retry['elapsed']:.0f}s, {retry['credits']:.4f} credits")
                else:
                    crashes.append({"tag": r["tag"], "error": r["error"], "retry_error": retry.get("error", "")})
                    print(f"    ✗ Retry FAILED: {retry.get('error', '')}")

        print(f"\n  Progress: {total_done}/30 done, {total_credits:.4f} credits, {len(crashes)} permanent crashes")

    print(f"\n{'='*60}")
    print(f"  ALL BATCHES COMPLETE")
    print(f"  Runs OK: {total_done}/30")
    print(f"  Total credits: {total_credits:.4f}")
    print(f"  Retried successfully: {retried_ok}")
    print(f"  Permanent crashes: {[c['tag'] for c in crashes]}")
    print(f"{'='*60}")

    if crashes:
        print("\nCRASH DETAILS:")
        for c in crashes:
            print(f"  {c['tag']}: {c['error']} / retry: {c['retry_error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
