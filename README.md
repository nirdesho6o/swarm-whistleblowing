# Swarm Whistleblowing Sprint

**Apart Swarm Alignment Hackathon, Nov 6–8 2026**

Does giving authority to whistleblowing reports increase false accusations in an AI swarm — and can correlated-agreement (CA) scoring keep reports honest?

## Updated results (v1.1/v1.2)

The sprint version (v1.0) is tagged `v1.0-sprint`. This branch adds two pre-registered rounds:
v1.1 Phase 1 (`PREREG_v1.1.md`) and v1.2 Phase 1.5 (`PREREG_v1.2.md`). Predictions were committed before
the runs. A prediction holds only if it goes the predicted way in at least 14 of 20 paired seeds, its 95%
bootstrap interval excludes zero, and the pooled difference reaches the stated minimum. The main measure is
the first-verdict flag rate: the share of honest agents' first verdicts on an entry that say `exploit`.
Full tables: `analysis/v1.1/phase1_results.md` and `analysis/v1.2/phase15_results.md`.

**Confirmatory (pre-registered)**
- **Decoy format drives false flags.** Hex decoys were flagged in 42.2% (114/270) of first verdicts. Decoys
  that look like honest work (v2) were flagged in 0.3% (1/312), a difference of +41.9 points
  [+33.9, +50.3], in 20 of 20 seeds. P7 (primary) predicted v2 decoys would still be flagged at least 3 points more than honest
  entries; it does not hold (-1.7 points [-2.7, -0.7]): v2 decoys were flagged no more than honest entries.
- **The v1.0 payment effect did not replicate.** In fresh Qwen runs, B and C differed little (42.2% vs 44.8%).
  An attention sentence without pay (E) was not reliably above B (P6a: +7.4 [-3.6, +18.5]). With v2 decoys,
  correlated-agreement pay added +0.3 points [-0.7, +1.5] (P8a). In GLM, C was above B by +14.0 [+5.1, +23.2]
  but only in 13 of 20 seeds (P9), and a fresh v1.2 GLM comparison gave +4.1 [-3.2, +10.5]. In Muse, C - B
  was -1.9 [-19.7, +16.3].
- **Asking agents to report narrows the gap between flagging and reporting** (P12 holds: +26.2
  [+11.9, +38.9], 15 of 20 seeds). Formal reports rose from 11 in B to 36 in B-ask.
- **Removing the authority of reports did not raise cheater flags** (P11: A - B = -12.9 [-30.9, +3.3]).
- **Stealthy cheating (v1.2).** Cheaters who submitted a plausible wrong answer from a stale answer key,
  instead of the odd `=!` prefix, were flagged *more*, not less: 74.1% (312/421) vs 32.0% (106/331)
  (P13a does not hold: -42.1 [-53.4, -30.3], 2 of 20 seeds). Reviewers seem to check answers, not process.
  Hex decoys were not reliably spared under stealthy cheating (P14a: +7.1 [-0.2, +14.2], interval touches
  zero). With v2 decoys the rates were about equal, as predicted (P14b holds: +1.9 [+0.3, +3.9], margin ±5).
  GLM attention and payment predictions (P15, P16) do not hold.

**Exploratory (not pre-registered)**
- `=!` entries with the correct number were flagged in 24.0% of first verdicts; with a wrong number, 85.4%.
  94.8% (147/155) of honest agents who opened only correct-number `=!` entries privately noted something odd,
  so most saw the trick but did not flag it (`analysis/v1.2/exploratory_v12.md`).
- **Hosted-model drift.** The same v1.0 code on Qwen gave a B decoy flag rate of 26.3% on Nov 7, 34.9% on
  Nov 25 and 45.3% in the v1.1 runs of Nov 23–24 (`analysis/v1.1/diag_v10code_B.md`). Comparisons across
  dates are therefore unreliable; v1.1 and v1.2 use same-period controls as the primary baseline.

Corrections are dated and kept in the results files; the independent checks (separate session) are in `verify/`.

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

## Notes after submission

- **Herding covariate.** Note (2026-11-25): `saw_prior_accusation` is computed for every review, but it is false in all reviews of all v1.0 and v1.1 runs. No agent posted an accusation on the board, and reports are not shown to other agents. Herding therefore cannot be measured in this design; `analysis/exploratory.md` §5 reports no herding effect.
- **Reports were not public.** The submitted report (PDF) describes reports as public ("file a public report", "reported it publicly"). In the environment, reports made with the `report` tool are seen only by the organizers' log and the removal count; other agents never see them, and the system prompt does not say who sees them. New outputs call them formal reports.

## Preexisting code

All code in this repository was written during the hackathon (Nov 6–8 2026). No preexisting code.
