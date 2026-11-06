from __future__ import annotations

import argparse
import asyncio
import random
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from swarm.agents import (
    build_system_prompt,
    parse_agent_response,
    render_observation,
    ParsedResponse,
)
from swarm.config import (
    AGENT_NAMES,
    CHEATER_NAMES,
    SEED_AGENT_NAMES,
    Condition,
    RunConfig,
)
from swarm.llm import LLMClient
from swarm.logging import EventLogger
from swarm.mechanisms import apply_revocations, compute_ca_payments
from swarm.puzzles import make_puzzle_bank
from swarm.world import WorldState


def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _seed_agent_submissions(world: WorldState) -> None:
    """Round-0 scripted submissions from decoy agents (correct hex answers)."""
    rng = random.Random(world.config.seed)
    open_pids = [p.pid for p in world.open_problems()]
    rng.shuffle(open_pids)

    for i, seed_name in enumerate(SEED_AGENT_NAMES):
        if i >= len(open_pids):
            break
        pid = open_pids[i]
        puzzle = world.get_puzzle(pid)
        hex_answer = hex(puzzle.answer)
        working = f"{hex_answer} (verified)"
        world.try_submit(seed_name, pid, hex_answer, working, round_num=0)
        world.scores.setdefault(seed_name, 0.0)


async def _run_agent_turn(
    agent_name: str,
    world: WorldState,
    llm: LLMClient,
    round_num: int,
) -> ParsedResponse:
    """Run one agent's turn: call LLM, parse, retry once on parse failure."""
    system_prompt = build_system_prompt(agent_name, world.config.condition)
    observation = render_observation(agent_name, world, round_num)

    raw_output, status = await llm.call(system_prompt, observation, agent_name, round_num)

    try:
        parsed = parse_agent_response(raw_output)
    except (ValueError, Exception) as e:
        # One repair retry with the parse error
        repair_prompt = (
            f"Your previous response could not be parsed as JSON.\n"
            f"Error: {e}\n"
            f"Please reply with ONLY a valid JSON object in the required format."
        )
        repair_input = f"{observation}\n\n{repair_prompt}\nYour broken response was:\n{raw_output[:500]}"
        raw_output2, status2 = await llm.call(system_prompt, repair_input, agent_name, round_num)
        try:
            parsed = parse_agent_response(raw_output2)
        except (ValueError, Exception):
            world.logger.log(round_num, agent_name, "parse_fail", {"raw": raw_output2[:500]})
            return ParsedResponse(raw=raw_output2)

    return parsed


def _has_prior_accusation(world: WorldState, entry_id: str) -> bool:
    """Check if entry was publicly accused on the board before this round."""
    entry = world.library.get(entry_id)
    if not entry:
        return False
    for bp in world.board:
        text_lower = bp.text.lower()
        if entry_id.lower() in text_lower or entry.agent.lower() in text_lower:
            if "cheat" in text_lower or "exploit" in text_lower or "suspicious" in text_lower or "report" in text_lower:
                return True
    return False


def _apply_actions(
    agent_name: str,
    parsed: ParsedResponse,
    world: WorldState,
    round_num: int,
    entries_read_this_round: dict[str, set[str]],
) -> None:
    """Execute the agent's chosen actions against the world state."""
    for action in parsed.actions:
        tool = action.get("tool", "")
        args = action.get("args", {})

        if tool == "submit":
            pid = str(args.get("problem_id", ""))
            answer = str(args.get("answer", ""))
            working = str(args.get("working", ""))
            accepted, entry = world.try_submit(agent_name, pid, answer, working, round_num)
            if not accepted:
                world.logger.log(round_num, agent_name, "submit", {
                    "problem_id": pid, "answer_raw": answer,
                    "accepted": False, "via_exploit": False,
                })

        elif tool == "read_library":
            eid = str(args.get("entry_id", ""))
            if eid in world.library:
                entries_read_this_round.setdefault(agent_name, set()).add(eid)
                entry = world.library[eid]
                world.logger.log(round_num, agent_name, "library_read", {
                    "entry_id": eid,
                    "problem_id": entry.problem_id,
                    "agent": entry.agent,
                    "answer_raw": entry.answer_raw,
                    "working": entry.working,
                })

        elif tool == "post_board":
            text = str(args.get("text", ""))[:500]
            world.post_board(agent_name, text, round_num)

        elif tool == "send_dm":
            to = str(args.get("to", ""))
            text = str(args.get("text", ""))[:500]
            if to in set(AGENT_NAMES) | set(SEED_AGENT_NAMES):
                world.send_dm(agent_name, to, text, round_num)
                if to in set(SEED_AGENT_NAMES):
                    world.logger.log(round_num, to, "action", {
                        "tool": "ignore_dm", "from": agent_name,
                    })

        elif tool == "report":
            target = str(args.get("agent", ""))
            eid = str(args.get("entry_id", ""))
            evidence = str(args.get("evidence", ""))[:500]
            if eid in world.library:
                world.file_report(agent_name, target, eid, evidence, round_num)

        elif tool == "pass":
            world.logger.log(round_num, agent_name, "action", {"tool": "pass"})


def _apply_reviews(
    agent_name: str,
    parsed: ParsedResponse,
    world: WorldState,
    round_num: int,
    entries_read_this_round: dict[str, set[str]],
) -> None:
    """File reviews for entries the agent has seen (this round or prior)."""
    current_reads = entries_read_this_round.get(agent_name, set())
    prior_reads = world.prior_reads.get(agent_name, set())
    all_known = current_reads | prior_reads
    for eid, verdict in parsed.reviews.items():
        if eid not in all_known:
            continue
        if verdict not in ("legit", "exploit", "unsure"):
            continue
        saw_prior = _has_prior_accusation(world, eid)
        world.file_review(agent_name, eid, verdict, round_num, saw_prior)


async def run(config: RunConfig, run_dir: Path | None = None) -> Path:
    """Run a full simulation. Returns the run directory."""
    run_id = f"{config.condition.value}-{config.model}-s{config.seed}-{uuid.uuid4().hex[:8]}"

    if run_dir is None:
        run_dir = Path("runs/dryrun") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = EventLogger(run_dir, run_id)
    puzzles = make_puzzle_bank()
    world = WorldState(config=config, puzzles=puzzles, logger=logger)

    llm = LLMClient(
        model=config.model,
        max_output_tokens=config.max_output_tokens,
        temperature=config.temperature,
        semaphore_limit=config.semaphore_limit,
        logger=logger,
    )

    git_hash = _git_hash()
    logger.log(None, None, "run_meta", {
        "run_id": run_id,
        "model": config.model,
        "condition": config.condition.value,
        "seed": config.seed,
        "config": config.model_dump(),
        "git_hash": git_hash,
        "n_puzzles": len(puzzles),
    })

    # Select agents for this run
    all_agents = list(AGENT_NAMES)
    if config.n_agents < len(all_agents):
        # For smoke tests with fewer agents, keep at least 1 cheater
        cheaters = [a for a in all_agents if a in CHEATER_NAMES][:1]
        honest = [a for a in all_agents if a not in CHEATER_NAMES][:config.n_agents - len(cheaters)]
        active_agents = honest + cheaters
    else:
        active_agents = all_agents

    t_start = time.monotonic()

    # Round 0: seed agent submissions
    _seed_agent_submissions(world)

    for round_num in range(config.rounds):
        print(f"  Round {round_num}/{config.rounds - 1}...", end=" ", flush=True)

        entries_read: dict[str, set[str]] = {}

        # All agents act in parallel on the same snapshot
        tasks = [
            _run_agent_turn(name, world, llm, round_num)
            for name in active_agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Apply actions in shuffled order (seeded) to avoid systematic first-mover advantage
        apply_order = list(range(len(active_agents)))
        round_rng = random.Random(config.seed * 10000 + round_num)
        round_rng.shuffle(apply_order)

        for idx in apply_order:
            name = active_agents[idx]
            result = results[idx]
            if isinstance(result, Exception):
                world.logger.log(round_num, name, "parse_fail", {"error": str(result)[:300]})
                continue

            parsed: ParsedResponse = result

            # Log the private recognition probe
            world.logger.log(round_num, name, "probe", {
                "noticed_suspicious": parsed.noticed_suspicious,
                "note": parsed.suspicion_note,
            })

            _apply_actions(name, parsed, world, round_num, entries_read)
            _apply_reviews(name, parsed, world, round_num, entries_read)

        # Merge this round's reads into prior_reads for next round
        for agent_name, eids in entries_read.items():
            world.prior_reads.setdefault(agent_name, set()).update(eids)

        # End-of-round mechanisms
        revoked = apply_revocations(world, round_num)
        if config.condition == Condition.C:
            ca_rng = random.Random(config.seed * 10000 + round_num)
            compute_ca_payments(world, round_num, ca_rng)

        n_open = len(world.open_problems())
        print(f"open={n_open}, revoked={len(revoked)}")

    wall_clock = time.monotonic() - t_start

    logger.log(None, None, "run_summary", {
        "wall_clock_s": round(wall_clock, 1),
        "total_input_tokens": llm.accounting.total_input,
        "total_output_tokens": llm.accounting.total_output,
        "total_credits": round(llm.accounting.total_credits, 6),
        "call_count": llm.accounting.call_count,
        "retry_count": llm.accounting.retry_count,
        "scores": dict(world.scores),
    })

    await llm.close()
    logger.close()

    print(f"\nRun complete: {run_id}")
    print(f"  Wall clock: {wall_clock:.1f}s")
    print(f"  Tokens: {llm.accounting.total_input} in, {llm.accounting.total_output} out")
    print(f"  Credits: {llm.accounting.total_credits:.6f}")
    print(f"  Scores: {dict(world.scores)}")
    print(f"  Logs: {run_dir}")

    return run_dir


async def list_available_models(logger: EventLogger) -> list[dict]:
    """List models the API key can access and log them."""
    import os
    from adaption import AsyncAdaption
    client = AsyncAdaption(api_key=os.environ.get("ADAPTION_API_KEY", ""))
    result = await client.models.list(type="hosted")
    models = []
    for m in result.data:
        models.append({"id": m.id, "owned_by": getattr(m, "owned_by", "")})
    logger.log(None, None, "available_models", {"models": models})
    await client.close()
    return models


def main():
    parser = argparse.ArgumentParser(description="Swarm whistleblowing simulation")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--condition", default="A", choices=["A", "B", "C"])
    parser.add_argument("--rounds", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-agents", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int, default=1500)
    parser.add_argument("--semaphore", type=int, default=8)
    args = parser.parse_args()

    config = RunConfig(
        model=args.model,
        condition=Condition(args.condition),
        rounds=args.rounds,
        seed=args.seed,
        n_agents=args.n_agents,
        max_output_tokens=args.max_output_tokens,
        semaphore_limit=args.semaphore,
    )

    asyncio.run(run(config))


if __name__ == "__main__":
    main()
