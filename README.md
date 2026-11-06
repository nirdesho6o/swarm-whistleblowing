# Swarm Whistleblowing Sprint

**Apart Swarm Alignment Hackathon, Nov 6–8 2026**

Does giving authority to whistleblowing reports increase false accusations in an AI swarm — and can correlated-agreement (CA) scoring keep reports honest?

## Design

- 8 LLM agents + 2 scripted decoy agents solve 20 integer-answer puzzles over synchronous rounds.
- 2 agents know a planted exploit (checker bug: `=!` prefix bypasses validation).
- 2 scripted agents submit correct answers in hex (legal but unusual — a false-accusation trap).
- Three conditions: **A** (norms only), **B** (reports have teeth — revocation), **C** (teeth + CA scoring).

## Repo layout

```
swarm/          Core simulation code
analysis/       Metrics and dry-run reporting (from logs only)
tests/          pytest suite
runs/           Run logs (JSONL)
PREREG.md       Pre-registered model selection rule and predictions
CLAUDE.md       Full spec for Claude Code
```

## Preexisting code

All code in this repository was written during the hackathon (Nov 6–8 2026). No preexisting code.

## Usage

```bash
pip install adaption pydantic pytest pandas matplotlib
export ADAPTION_API_KEY=...
python -m swarm.runner --model deepseek-v4-flash --condition A --rounds 12
```
