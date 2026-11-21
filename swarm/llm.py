from __future__ import annotations

import asyncio
import hashlib
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
load_dotenv()

from adaption import AsyncAdaption

from swarm.logging import EventLogger
from swarm.providers import ProviderError, RateLimited, make_backend, split_provider


COST_PER_M: dict[str, tuple[float, float]] = {
    "qwen3.5-397b": (0.55, 3.50),
    "glm-5.2": (0.104, 4.40),
    "deepseek-v4-flash": (0.044, 0.133),
    # v1.1: Meta Model API list prices in USD per 1M tokens (dev.meta.ai/docs/pricing-rate-limits, 2026-11-22).
    # Gemini free tier costs 0. Adaption models not listed here fall back to the API-reported usage.cost.
    "meta:muse-spark-1.3": (1.25, 4.25),
    "meta:muse-spark-1.2": (1.25, 4.25),
    "meta:muse-spark-1.1": (1.25, 4.25),
    "meta:muse-wonder-1.0": (4.00, 20.00),
    "meta:muse-ember-1.0": (0.10, 0.50),  # <=200K-token requests
}


@dataclass
class TokenAccounting:
    total_input: int = 0
    total_output: int = 0
    total_reasoning: int = 0
    total_credits: float = 0.0
    call_count: int = 0
    retry_count: int = 0

    def record(self, model: str, input_tokens: int, output_tokens: int, reasoning_tokens: int = 0,
               reported_cost: float | None = None) -> None:
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.total_reasoning += reasoning_tokens
        self.call_count += 1
        if model not in COST_PER_M and reported_cost is not None:
            # v1.1: models without a listed price use the provider-reported cost.
            self.total_credits += reported_cost
            return
        in_cost, out_cost = COST_PER_M.get(model, (0.0, 0.0))
        self.total_credits += input_tokens * in_cost / 1_000_000 + output_tokens * out_cost / 1_000_000


class LLMClient:
    def __init__(self, model: str, max_output_tokens: int, temperature: float,
                 semaphore_limit: int, logger: EventLogger):
        self.provider, self._api_model = split_provider(model)
        self._backend = None
        self._client = None
        if self.provider == "adaption":
            api_key = os.environ.get("ADAPTION_API_KEY")
            if not api_key:
                raise RuntimeError("ADAPTION_API_KEY env var not set")
            self._client = AsyncAdaption(api_key=api_key)
        else:
            self._backend = make_backend(self.provider, self._api_model)
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self._sem = asyncio.Semaphore(semaphore_limit)
        self._logger = logger
        self.accounting = TokenAccounting()

    async def call(
        self,
        instructions: str,
        user_content: str,
        agent: str,
        round_num: int,
    ) -> tuple[str, str]:
        """Call the LLM with retries and backoff.

        Returns (output_text, status).
        """
        prompt_hash = hashlib.sha256((instructions + user_content).encode()).hexdigest()[:16]
        retries = 0
        max_retries = 5
        last_error: Exception | None = None

        while retries <= max_retries:
            async with self._sem:
                t0 = time.monotonic()
                try:
                    if self._backend is None:
                        response = await self._client.responses.create(
                            model=self.model,
                            instructions=instructions,
                            input=[{"role": "user", "content": user_content}],
                            max_output_tokens=self.max_output_tokens,
                            temperature=self.temperature,
                        )
                        latency = time.monotonic() - t0
                        status = response.status

                        input_tokens = response.usage.input_tokens
                        output_tokens = response.usage.output_tokens
                        reasoning_tokens = 0
                        if hasattr(response.usage, "output_tokens_details") and response.usage.output_tokens_details:
                            reasoning_tokens = getattr(response.usage.output_tokens_details, "reasoning_tokens", 0) or 0
                        output_text = response.output_text
                        reported_cost = getattr(response.usage, "cost", None)
                    else:
                        res = await self._backend.create(
                            instructions, user_content, self.max_output_tokens, self.temperature,
                        )
                        latency = time.monotonic() - t0
                        status = res.status
                        input_tokens = res.input_tokens
                        output_tokens = res.output_tokens
                        reasoning_tokens = res.reasoning_tokens
                        output_text = res.text
                        reported_cost = None

                    self.accounting.record(self.model, input_tokens, output_tokens, reasoning_tokens,
                                           reported_cost=reported_cost)

                    self._logger.log(round_num, agent, "llm_call", {
                        "prompt_hash": prompt_hash,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "reasoning_tokens": reasoning_tokens,
                        "latency": round(latency, 3),
                        "retries": retries,
                        "status": status,
                    })
                    self._logger.log_raw(round_num, agent, prompt_hash, output_text)

                    return output_text, status

                except ProviderError as e:
                    # Non-retryable 4xx from a non-Adaption provider (never raised on the Adaption path)
                    last_error = e
                    break
                except Exception as e:
                    last_error = e
                    retries += 1
                    self.accounting.retry_count += 1
                    if retries > max_retries:
                        break
                    backoff = min(2 ** retries + random.random(), 30)
                    if isinstance(e, RateLimited) and e.retry_after:
                        # Provider asked us to wait (Meta Retry-After / Gemini retryDelay), capped at 120 s
                        backoff = max(backoff, min(e.retry_after + random.random(), 120))
                    self._logger.log(round_num, agent, "llm_call", {
                        "prompt_hash": prompt_hash,
                        "retries": retries,
                        "error": str(e)[:200],
                        "status": "retry",
                    })
                    await asyncio.sleep(backoff)

        self._logger.log(round_num, agent, "llm_call", {
            "prompt_hash": prompt_hash,
            "retries": retries,
            "error": str(last_error)[:200],
            "status": "failed",
        })
        raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_error}")

    async def list_models(self) -> list[dict[str, Any]]:
        if self._backend is not None:
            return await self._backend.list_models()
        result = await self._client.models.list(type="hosted")
        models = []
        for m in result.data:
            models.append({"id": m.id, "owned_by": getattr(m, "owned_by", "")})
        return models

    async def close(self) -> None:
        if self._backend is not None:
            await self._backend.close()
        else:
            await self._client.close()
