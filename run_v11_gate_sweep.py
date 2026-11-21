"""v1.1 model gate sweep (DRY RUNS ONLY; never used in results).

One run of setup B, seed 99, per model, identical prompts and settings for every model
(20 rounds, 8 LLM agents + 2 v1 decoys, temperature 0.7, max_output_tokens 1500). Output:
runs/v1.1/gate_sweep/<model>/ . Table: python analysis/v1.1/gate_sweep.py

Models: every chat model the Adaption key lists, plus Meta (meta:<id>) and Gemini (gemini:<id>) models
given on the command line. Meta/Gemini models are skipped if their API key env var is not set.
Usage: python run_v11_gate_sweep.py [--extra meta:muse-spark-1.3 gemini:gemini-3.8-flash] [--only m1 m2]
"""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from swarm.config import Condition, RunConfig  # noqa: E402
from swarm.providers import split_provider  # noqa: E402
from swarm.runner import run  # noqa: E402

OUT = Path("runs/v1.1/gate_sweep")
SEED = 99
ROUNDS = 20
MAX_CONCURRENT = 3
KEY_ENV = {"adaption": "ADAPTION_API_KEY", "meta": "META_API_KEY", "gemini": "GEMINI_API_KEY"}


async def adaption_models() -> list[str]:
    from adaption import AsyncAdaption
    c = AsyncAdaption(api_key=os.environ["ADAPTION_API_KEY"])
    r = await c.models.list(type="hosted")
    await c.close()
    return [m.id for m in r.data]


def dir_name(model: str) -> str:
    return model.replace(":", "__").replace("/", "_")


async def run_one(model: str, sem: asyncio.Semaphore) -> dict:
    provider, _ = split_provider(model)
    if not os.environ.get(KEY_ENV[provider]):
        return {"model": model, "ok": False, "skipped": f"{KEY_ENV[provider]} not set"}
    async with sem:
        cfg = RunConfig(model=model, condition=Condition.B, rounds=ROUNDS, seed=SEED, n_agents=8,
                        max_output_tokens=1500, temperature=0.7, semaphore_limit=8)
        t0 = time.monotonic()
        try:
            await run(cfg, OUT / dir_name(model))
            return {"model": model, "ok": True, "elapsed_s": round(time.monotonic() - t0, 1)}
        except Exception as e:
            return {"model": model, "ok": False, "error": str(e)[:300], "elapsed_s": round(time.monotonic() - t0, 1)}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    models = args.only if args.only else (await adaption_models()) + args.extra
    OUT.mkdir(parents=True, exist_ok=True)
    print("Models:", models, flush=True)
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results = await asyncio.gather(*(run_one(m, sem) for m in models))
    with open(OUT / "sweep_status.jsonl", "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
            print(r, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
