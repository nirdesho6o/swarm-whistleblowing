"""v1.2 dry runs (exploratory, never used in results): one run per new cell, seed 99, real-run settings.

Cells: qwen3.5-397b B-stealth-v1, B-stealth-v2 (setup B rules, stale-answer-key exploit), glm-5.2 E.
Output: runs/v1.2/dryrun/<model_dir>/<cell>_seed99/. Runs all three at once (3 at a time, as in v1.1).
"""
import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

from swarm.config import Condition, RunConfig
from swarm.runner import run

load_dotenv(Path(__file__).resolve().parent / ".env")
OUT = Path(__file__).resolve().parent / "runs/v1.2/dryrun"
CELLS = [  # (model, cell name, condition, decoy_version, exploit)
    ("qwen3.5-397b", "B-stealth-v1", Condition.B, 1, "stealth"),
    ("qwen3.5-397b", "B-stealth-v2", Condition.B, 2, "stealth"),
    ("glm-5.2", "E", Condition.E, 1, "odd"),
]


async def one(model, name, cond, dv, exploit):
    cfg = RunConfig(model=model, condition=cond, rounds=20, seed=99, n_agents=8, max_output_tokens=1500,
                    temperature=0.7, semaphore_limit=8, decoy_version=dv, exploit=exploit)
    d = OUT / model.replace(":", "__") / f"{name}_seed99"
    t0 = time.monotonic()
    try:
        await run(cfg, d)
        print(f"DONE {model} {name} {(time.monotonic() - t0) / 60:.1f} min", flush=True)
    except Exception as e:
        print(f"CRASH {model} {name}: {str(e)[:300]}", flush=True)


async def main():
    await asyncio.gather(*(one(*c) for c in CELLS))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
