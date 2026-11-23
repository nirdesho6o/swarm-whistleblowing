"""v1.1 dry runs (never used in results): one run of each new Phase 1 setup, seed 99, qwen3.5-397b,
all launched at once to check whether 6 runs in parallel stay free of rate-limit errors.
Output: runs/v1.1/dryrun_setups/<setup>/ . Summary: analysis/v1.1/dryrun_setups.md (analysis/v1.1/dryrun_setups.py)
"""
import asyncio
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from swarm.config import Condition, RunConfig  # noqa: E402
from swarm.runner import run  # noqa: E402

OUT = Path("runs/v1.1/dryrun_setups")
SETUPS = {  # name: (condition, decoy_version)
    "E": (Condition.E, 1),
    "E-CA": (Condition.E_CA, 1),
    "B-ask": (Condition.B_ASK, 1),
    "B-v2": (Condition.B, 2),
    "C-v2": (Condition.C, 2),
    "D-v2": (Condition.D, 2),
}


async def one(name, cond, dv):
    cfg = RunConfig(model="qwen3.5-397b", condition=cond, rounds=20, seed=99, n_agents=8,
                    max_output_tokens=1500, temperature=0.7, semaphore_limit=8, decoy_version=dv)
    t0 = time.monotonic()
    try:
        await run(cfg, OUT / name)
        return {"setup": name, "ok": True, "elapsed_s": round(time.monotonic() - t0, 1)}
    except Exception as e:
        return {"setup": name, "ok": False, "error": str(e)[:300], "elapsed_s": round(time.monotonic() - t0, 1)}


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = await asyncio.gather(*(one(n, c, d) for n, (c, d) in SETUPS.items()))
    with open(OUT / "status.jsonl", "a") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
            print(r, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
