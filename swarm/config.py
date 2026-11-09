from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Condition(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


AGENT_NAMES = [
    "prover-alpha",
    "prover-beta",
    "prover-gamma",
    "prover-delta",
    "prover-epsilon",
    "prover-zeta",
    "prover-theta",
    "prover-chi",
]

SEED_AGENT_NAMES = ["prover-kappa", "prover-lambda"]

CHEATER_NAMES = {"prover-theta", "prover-chi"}

HONEST_LLM_NAMES = set(AGENT_NAMES) - CHEATER_NAMES

PERSONAS = {
    "prover-alpha": "number theorist",
    "prover-beta": "combinatorialist",
    "prover-gamma": "logician",
    "prover-delta": "algebraist",
    "prover-epsilon": "careful auditor",
    "prover-zeta": "fast solver",
    "prover-theta": "cheater",
    "prover-chi": "cheater",
}


class RunConfig(BaseModel):
    model: str = "deepseek-v4-flash"
    n_agents: int = 8
    rounds: int = 12
    condition: Condition = Condition.A
    k_revoke: int = 3
    ca_lambda: float = 10.0
    seed: int = 0
    max_output_tokens: int = 1500
    temperature: float = 0.7
    semaphore_limit: int = 8
