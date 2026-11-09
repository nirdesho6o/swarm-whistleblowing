# Swarm Whistleblowing Sprint

**Apart Swarm Alignment Hackathon, Nov 6–8 2026**

Does giving authority to whistleblowing reports increase false accusations in an AI swarm — and can correlated-agreement (CA) scoring keep reports honest?

## Design

- 8 LLM agents + 2 scripted decoy agents solve 20 integer-answer puzzles over synchronous rounds.
- 2 agents know a planted exploit (checker bug: `=!` prefix bypasses validation).
- 2 scripted agents submit correct answers in hex (legal but unusual — a false-accusation trap).
- Four conditions: **A** (norms only), **B** (reports have teeth — revocation), **C** (teeth + CA scoring), **D** (teeth + flat per-verdict pay — control for C).

## Repo layout

```
swarm/          Core simulation code
  config.py     RunConfig, agent names, roles
  llm.py        Async Adaption wrapper with retries, semaphore, token accounting
  puzzles.py    Puzzle bank + exact checker with planted exploit
  world.py      Shared state: library, board, DMs, reviews, reports, scores
  agents.py     Prompt builders, observation rendering, JSON action parsing
  mechanisms.py Revocation (B/C/D), CA scoring (C), flat pay (D)
  runner.py     Round loop and CLI entry point
  logging.py    JSONL event logger
analysis/       Metrics and dry-run reporting (from logs only)
  metrics.py    All metrics computed from events.jsonl against ground truth
  dryrun_report.py  Model-selection table and PREREG rule application
tests/          pytest suite (81 tests)
runs/           Run logs (JSONL, gitignored)
PREREG.md       Pre-registered model selection rule and predictions
CLAUDE.md       Full spec for Claude Code
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install adaption pydantic pytest python-dotenv pandas matplotlib
```

Copy `.env` and fill in your API key:

```bash
cp .env.example .env   # or just edit .env directly
# Set ADAPTION_API_KEY=pt_live_...
```

The `.env` file is gitignored and loaded automatically by the runner.

## Usage

```bash
# Smoke test
python -m swarm.runner --model deepseek-v4-flash --condition A --rounds 4 --n-agents 3

# Full dry run (condition A, 12 rounds, 8 LLM agents + 2 seed agents)
python -m swarm.runner --model deepseek-v4-flash --condition A --rounds 12

# Run analysis report
python -m analysis.dryrun_report --base runs/dryrun2

# Run tests
pytest tests/ -v
```

## Preexisting code

All code in this repository was written during the hackathon (Nov 6–8 2026). No preexisting code.
