"""v1.1: Meta and Gemini backends, routing, rate-limit handling and key hygiene. No network."""
import asyncio
import json

import httpx
import pytest

from swarm import llm as llm_mod
from swarm import providers
from swarm.llm import LLMClient, TokenAccounting
from swarm.logging import EventLogger
from swarm.providers import GeminiBackend, MetaBackend, RateLimited, split_provider

META_KEY = "LLM_123_test-secret-meta"
GEMINI_KEY = "AIza-test-secret-gemini"


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setenv("META_API_KEY", META_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", GEMINI_KEY)
    providers.GeminiBackend._limiters.clear()


def _run(coro):
    return asyncio.run(coro)


def test_split_provider():
    assert split_provider("qwen3.5-397b") == ("adaption", "qwen3.5-397b")
    assert split_provider("gemma-4-31b-it") == ("adaption", "gemma-4-31b-it")
    assert split_provider("meta:muse-spark-1.3") == ("meta", "muse-spark-1.3")
    assert split_provider("gemini:gemini-3.8-flash") == ("gemini", "gemini-3.8-flash")


def test_adaption_path_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("ADAPTION_API_KEY", "x")
    c = LLMClient("qwen3.5-397b", 1500, 0.7, 8, EventLogger(tmp_path, "t"))
    assert c.provider == "adaption" and c._backend is None and c._client is not None
    assert c.model == "qwen3.5-397b"


def test_qwen_accounting_ignores_reported_cost():
    a = TokenAccounting()
    a.record("qwen3.5-397b", 1_000_000, 1_000_000, reported_cost=999.0)
    assert a.total_credits == pytest.approx(0.55 + 3.50)
    b = TokenAccounting()
    b.record("gemma-4-31b-it", 10, 10, reported_cost=0.25)
    assert b.total_credits == pytest.approx(0.25)


# ---------------- Meta ----------------

def test_meta_request_body_and_headers():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{\"actions\": []}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7,
                      "completion_tokens_details": {"reasoning_tokens": 3}},
        })

    b = MetaBackend("muse-spark-1.3", transport=httpx.MockTransport(handler))
    res = _run(b.create("SYS", "USER", 1500, 0.7))
    assert seen["url"] == "https://api.meta.ai/v1/chat/completions"
    assert seen["auth"] == f"Bearer {META_KEY}"
    assert seen["body"] == {
        "model": "muse-spark-1.3",
        "messages": [{"role": "developer", "content": "SYS"}, {"role": "user", "content": "USER"}],
        "max_completion_tokens": 1500, "temperature": 0.7, "reasoning_effort": "minimal",
    }
    assert (res.text, res.status, res.input_tokens, res.output_tokens, res.reasoning_tokens) == \
        ("{\"actions\": []}", "completed", 11, 7, 3)


def test_meta_length_is_incomplete():
    r = MetaBackend.parse({"choices": [{"message": {"content": "x"}, "finish_reason": "length"}], "usage": {}})
    assert r.status == "incomplete"


def test_meta_429_retry_after_and_key_scrubbed():
    def handler(req):
        return httpx.Response(429, headers={"Retry-After": "15"},
                              json={"error": {"message": f"slow down {META_KEY}", "type": "rate_limit_error"}})

    b = MetaBackend("muse-spark-1.3", transport=httpx.MockTransport(handler))
    with pytest.raises(RateLimited) as ei:
        _run(b.create("s", "u", 10, 0.7))
    assert ei.value.retry_after == 15.0
    assert META_KEY not in str(ei.value)


# ---------------- Gemini ----------------

def test_gemini_request_body_and_headers():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "think", "thought": True}, {"text": "ANSWER"}]},
                            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 5, "thoughtsTokenCount": 4},
        })

    b = GeminiBackend("gemini-3.8-flash", transport=httpx.MockTransport(handler), rpm=0)
    res = _run(b.create("SYS", "USER", 1500, 0.7))
    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
    assert seen["key"] == GEMINI_KEY and GEMINI_KEY not in seen["url"]
    assert seen["body"] == {
        "systemInstruction": {"parts": [{"text": "SYS"}]},
        "contents": [{"role": "user", "parts": [{"text": "USER"}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500,
                             "thinkingConfig": {"thinkingLevel": "MINIMAL"}},
    }
    assert (res.text, res.status, res.input_tokens, res.output_tokens, res.reasoning_tokens) == \
        ("ANSWER", "completed", 20, 9, 4)


def test_gemini_no_thinking_config_for_old_models():
    b = GeminiBackend("gemini-2.5-flash", rpm=0)
    assert "thinkingConfig" not in b.build_body("s", "u", 10, 0.7)["generationConfig"]


def test_gemini_statuses():
    assert GeminiBackend.parse({"candidates": [{"finishReason": "MAX_TOKENS"}]}).status == "incomplete"
    assert GeminiBackend.parse({"candidates": [{"finishReason": "SAFETY"}]}).status == "safety"
    assert GeminiBackend.parse({"promptFeedback": {"blockReason": "OTHER"}}).status == "blocked_other"


def test_gemini_429_retry_delay_from_body():
    def handler(req):
        return httpx.Response(429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17s"}]}})

    b = GeminiBackend("gemini-3.8-flash", transport=httpx.MockTransport(handler), rpm=0)
    with pytest.raises(RateLimited) as ei:
        _run(b.create("s", "u", 10, 0.7))
    assert ei.value.retry_after == 17.0


def test_rpm_limiter_blocks_over_limit(monkeypatch):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)
        lim._times.popleft()  # pretend the window moved on

    lim = providers._RpmLimiter(2)
    monkeypatch.setattr(providers.asyncio, "sleep", fake_sleep)

    async def go():
        for _ in range(3):
            await lim.acquire()

    _run(go())
    assert len(sleeps) == 1


# ---------------- LLMClient integration: retries + key hygiene ----------------

def test_llmclient_retries_on_429_then_succeeds_and_never_logs_key(monkeypatch, tmp_path):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": {"message": "x"}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        })

    slept = []

    async def fake_sleep(s):
        slept.append(s)

    monkeypatch.setattr(llm_mod.asyncio, "sleep", fake_sleep)
    logger = EventLogger(tmp_path, "t")
    c = LLMClient("meta:muse-spark-1.3", 1500, 0.7, 8, logger)
    c._backend = MetaBackend("muse-spark-1.3", transport=httpx.MockTransport(handler))
    text, status = _run(c.call("SYS", "USER", "prover-alpha", 0))
    logger.close()
    assert (text, status) == ("OK", "completed")
    assert calls["n"] == 2 and slept and slept[0] >= 2.0
    for f in tmp_path.iterdir():
        assert META_KEY not in f.read_text()
        assert GEMINI_KEY not in f.read_text()


def test_llmclient_does_not_retry_400(monkeypatch, tmp_path):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "bad"}})

    async def fake_sleep(s):
        pass

    monkeypatch.setattr(llm_mod.asyncio, "sleep", fake_sleep)
    c = LLMClient("meta:muse-spark-1.3", 1500, 0.7, 8, EventLogger(tmp_path, "t"))
    c._backend = MetaBackend("muse-spark-1.3", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        _run(c.call("s", "u", "a", 0))
    assert calls["n"] == 1


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiBackend("gemini-3.8-flash")
