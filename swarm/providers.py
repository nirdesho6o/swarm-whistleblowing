"""Non-Adaption chat backends (v1.1): Meta Model API (Muse) and Gemini API (free tier).

Model strings route by prefix:  "meta:<model-id>"  and  "gemini:<model-id>".  Anything without a
prefix goes to the original Adaption path in swarm/llm.py, which is unchanged.

Both backends send the same instructions (system prompt), the same single user message,
the same temperature and the same output-token cap that the Adaption path sends.

API keys are read from env vars at construction time (META_API_KEY, GEMINI_API_KEY), sent only in
request headers, and scrubbed from every error string. They are never logged or written to disk.

Docs used (read 2026-11-22):
- Meta: https://dev.meta.ai/docs/protocols/chat-completions  (OpenAI-compatible, POST /v1/chat/completions,
  `max_completion_tokens` includes reasoning tokens, `reasoning_effort` cannot be "none", 429 + Retry-After)
- Gemini: https://aistudio.google.com/api-reference/generate-content  (POST
  /v1beta/models/{model}:generateContent, `systemInstruction`, `generationConfig`, `usageMetadata`,
  429 RESOURCE_EXHAUSTED)
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import httpx

META_BASE_URL = "https://api.meta.ai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

PROVIDER_PREFIXES = ("meta:", "gemini:")


def split_provider(model: str) -> tuple[str, str]:
    """'meta:muse-spark-1.3' -> ('meta', 'muse-spark-1.3'); 'qwen3.5-397b' -> ('adaption', 'qwen3.5-397b')."""
    for p in PROVIDER_PREFIXES:
        if model.startswith(p):
            return p[:-1], model[len(p):]
    return "adaption", model


@dataclass
class BackendResult:
    text: str
    status: str  # "completed" | "incomplete" | other provider-specific status, lower-case
    input_tokens: int
    output_tokens: int  # visible + reasoning tokens (as billed)
    reasoning_tokens: int


class RateLimited(Exception):
    """429 from a provider. retry_after is the server-suggested wait in seconds, if any."""

    def __init__(self, message: str, retry_after: float | None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderError(Exception):
    """Non-retryable request error (4xx other than 429)."""


def _scrub(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def _parse_retry_after(headers: httpx.Headers) -> float | None:
    v = headers.get("retry-after")
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


class _RpmLimiter:
    """Sliding-window requests-per-minute limiter (client side)."""

    def __init__(self, rpm: int):
        self.rpm = rpm
        self._times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self.rpm <= 0:
            return
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._times and now - self._times[0] >= 60.0:
                    self._times.popleft()
                if len(self._times) < self.rpm:
                    self._times.append(now)
                    return
                await asyncio.sleep(60.0 - (now - self._times[0]) + 0.05)


class _HttpBackend:
    env_var = ""
    base_url = ""

    def __init__(self, model: str, transport: httpx.AsyncBaseTransport | None = None):
        key = os.environ.get(self.env_var)
        if not key:
            raise RuntimeError(f"{self.env_var} env var not set")
        self._key = key
        self.model = model
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=180.0, transport=transport)

    def _raise_for_status(self, r: httpx.Response) -> None:
        if r.status_code == 429:
            raise RateLimited(_scrub(f"429 rate limited: {r.text[:300]}", self._key), self._retry_after(r))
        if r.status_code >= 500:
            # Retryable by the caller's generic retry loop
            raise RuntimeError(_scrub(f"{r.status_code} server error: {r.text[:300]}", self._key))
        if r.status_code >= 400:
            raise ProviderError(_scrub(f"{r.status_code} request error: {r.text[:300]}", self._key))

    def _retry_after(self, r: httpx.Response) -> float | None:
        return _parse_retry_after(r.headers)

    async def close(self) -> None:
        await self._http.aclose()


class MetaBackend(_HttpBackend):
    """Meta Model API, OpenAI-compatible Chat Completions.

    Muse chat models always reason and `max_completion_tokens` counts reasoning tokens, so we send
    reasoning_effort="minimal" (lowest accepted value; "none" returns 400) to keep the visible-output
    budget comparable to non-reasoning models. This is a provider setting, not a prompt change.
    """

    env_var = "META_API_KEY"
    base_url = META_BASE_URL
    reasoning_effort = "minimal"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def build_body(self, instructions: str, user_content: str, max_output_tokens: int, temperature: float) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "developer", "content": instructions},
                {"role": "user", "content": user_content},
            ],
            "max_completion_tokens": max_output_tokens,
            "temperature": temperature,
            "reasoning_effort": self.reasoning_effort,
        }

    async def create(self, instructions: str, user_content: str, max_output_tokens: int,
                     temperature: float) -> BackendResult:
        body = self.build_body(instructions, user_content, max_output_tokens, temperature)
        try:
            r = await self._http.post("/chat/completions", json=body, headers=self._headers())
        except httpx.HTTPError as e:
            raise RuntimeError(_scrub(f"meta transport error: {e!r}", self._key)) from None
        self._raise_for_status(r)
        return self.parse(r.json())

    @staticmethod
    def parse(data: dict[str, Any]) -> BackendResult:
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        finish = choice.get("finish_reason") or "unknown"
        status = {"stop": "completed", "length": "incomplete"}.get(finish, finish)
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        return BackendResult(
            text=text,
            status=status,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            reasoning_tokens=int(details.get("reasoning_tokens") or 0),
        )

    async def list_models(self) -> list[dict[str, Any]]:
        r = await self._http.get("/models", headers=self._headers())
        self._raise_for_status(r)
        return [{"id": m.get("id"), "owned_by": m.get("owned_by", "")} for m in r.json().get("data", [])]


class GeminiBackend(_HttpBackend):
    """Gemini API generateContent, intended for the free tier.

    - Client-side RPM limit from env GEMINI_RPM (default 10; free-tier limits are per project and
      shown only in AI Studio, so set this to the project's actual limit).
    - 429 RESOURCE_EXHAUSTED -> RateLimited, using RetryInfo.retryDelay or Retry-After if present.
    - Thinking: for Gemini 3+ models we request thinkingLevel MINIMAL (docs: "Little to no thinking";
      using thinkingLevel on earlier models is an error). Older models get no thinkingConfig.
    - Docs say temperature is "silently ignored on Gemini 3.6 Flash and newer models"; we still send 0.7.
    """

    env_var = "GEMINI_API_KEY"
    base_url = GEMINI_BASE_URL
    _limiters: dict[str, _RpmLimiter] = {}

    def __init__(self, model: str, transport: httpx.AsyncBaseTransport | None = None, rpm: int | None = None):
        super().__init__(model, transport)
        rpm = rpm if rpm is not None else int(os.environ.get("GEMINI_RPM", "10"))
        # One limiter per model, shared by all clients in the process (limits are per project).
        self._limiter = GeminiBackend._limiters.setdefault(model, _RpmLimiter(rpm))

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self._key, "Content-Type": "application/json"}

    def _thinking_config(self) -> dict | None:
        m = re.match(r"gemini-(\d+)", self.model)
        if m and int(m.group(1)) >= 3:
            return {"thinkingLevel": "MINIMAL"}
        return None

    def build_body(self, instructions: str, user_content: str, max_output_tokens: int, temperature: float) -> dict:
        gen: dict[str, Any] = {"temperature": temperature, "maxOutputTokens": max_output_tokens}
        tc = self._thinking_config()
        if tc:
            gen["thinkingConfig"] = tc
        return {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": gen,
        }

    def _retry_after(self, r: httpx.Response) -> float | None:
        ra = _parse_retry_after(r.headers)
        if ra is not None:
            return ra
        try:
            for d in r.json().get("error", {}).get("details", []):
                delay = d.get("retryDelay")
                if delay and str(delay).endswith("s"):
                    return float(str(delay)[:-1])
        except Exception:
            pass
        return None

    async def create(self, instructions: str, user_content: str, max_output_tokens: int,
                     temperature: float) -> BackendResult:
        await self._limiter.acquire()
        body = self.build_body(instructions, user_content, max_output_tokens, temperature)
        try:
            r = await self._http.post(f"/models/{self.model}:generateContent", json=body, headers=self._headers())
        except httpx.HTTPError as e:
            raise RuntimeError(_scrub(f"gemini transport error: {e!r}", self._key)) from None
        self._raise_for_status(r)
        return self.parse(r.json())

    @staticmethod
    def parse(data: dict[str, Any]) -> BackendResult:
        cands = data.get("candidates") or []
        cand = cands[0] if cands else {}
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        finish = cand.get("finishReason")
        if finish is None:
            block = (data.get("promptFeedback") or {}).get("blockReason")
            status = f"blocked_{block.lower()}" if block else "unknown"
        else:
            status = {"STOP": "completed", "MAX_TOKENS": "incomplete"}.get(finish, finish.lower())
        u = data.get("usageMetadata") or {}
        thoughts = int(u.get("thoughtsTokenCount") or 0)
        return BackendResult(
            text=text,
            status=status,
            input_tokens=int(u.get("promptTokenCount") or 0),
            output_tokens=int(u.get("candidatesTokenCount") or 0) + thoughts,
            reasoning_tokens=thoughts,
        )

    async def list_models(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page_token = None
        while True:
            params = {"pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token
            r = await self._http.get("/models", headers=self._headers(), params=params)
            self._raise_for_status(r)
            data = r.json()
            for m in data.get("models", []):
                out.append({
                    "id": m.get("name", "").removeprefix("models/"),
                    "display_name": m.get("displayName"),
                    "methods": m.get("supportedGenerationMethods", []),
                    "thinking": m.get("thinking"),
                })
            page_token = data.get("nextPageToken")
            if not page_token:
                return out


def make_backend(provider: str, model: str) -> _HttpBackend:
    if provider == "meta":
        return MetaBackend(model)
    if provider == "gemini":
        return GeminiBackend(model)
    raise ValueError(f"unknown provider {provider}")
