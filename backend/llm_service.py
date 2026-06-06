"""
LLM Provider Abstraction — Primary: Emergent, Fallback: Direct APIs.
Prevents single-point-of-failure on any one provider.

task="reasoning"  → Claude Sonnet (deep analysis, CV tailoring)
task="fast"       → Gemini Flash  (classification, quick scoring)
task="structured" → GPT-4         (guaranteed JSON schema)

Circuit breaker: per-provider sliding-window (10 calls, >50% errors → open for 60s).
"""
import asyncio
import logging
import time
from collections import deque
from typing import Literal

logger = logging.getLogger(__name__)
TaskType = Literal["reasoning", "fast", "structured"]

ROUTING = {
    "reasoning":  {"emergent": ("anthropic", "claude-sonnet-4-5-20250929"), "direct": "anthropic"},
    "fast":       {"emergent": ("gemini",    "gemini-3-flash-preview"),     "direct": "gemini"},
    "structured": {"emergent": ("openai",    "gpt-5.1"),                    "direct": "openai"},
}

# ── Circuit Breaker ───────────────────────────────────────────────────────────
_WINDOW   = 10    # last N calls tracked per provider
_ERR_RATE = 0.5   # open if error rate > 50%
_OPEN_TTL = 60    # seconds to stay open before half-open retry

class _CircuitBreaker:
    def __init__(self):
        self._history: dict[str, deque] = {}   # provider → deque of bool (True=ok)
        self._open_at: dict[str, float] = {}   # provider → epoch when opened

    def _key(self, fn_name: str) -> str:
        return fn_name.replace("_call_", "")

    def is_open(self, fn_name: str) -> bool:
        key = self._key(fn_name)
        opened = self._open_at.get(key)
        if not opened:
            return False
        if time.monotonic() - opened >= _OPEN_TTL:
            # half-open: allow one probe
            logger.info("Circuit %s half-open (probe allowed)", key)
            del self._open_at[key]
            return False
        return True

    def record(self, fn_name: str, success: bool):
        key = self._key(fn_name)
        hist = self._history.setdefault(key, deque(maxlen=_WINDOW))
        hist.append(success)
        if len(hist) >= _WINDOW:
            error_rate = hist.count(False) / len(hist)
            if error_rate > _ERR_RATE and key not in self._open_at:
                logger.warning("Circuit OPEN for provider=%s (error_rate=%.0f%%)", key, error_rate * 100)
                self._open_at[key] = time.monotonic()

    def status(self) -> dict:
        out = {}
        for key, hist in self._history.items():
            opened = self._open_at.get(key)
            out[key] = {
                "state": "open" if opened else "closed",
                "error_rate": round(hist.count(False) / len(hist), 2) if hist else 0.0,
                "samples": len(hist),
            }
        return out

_cb = _CircuitBreaker()

# ── Provider callers ──────────────────────────────────────────────────────────

async def _call_emergent(task, system, user, session_id):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from config import settings
    key = settings.EMERGENT_LLM_KEY or ""
    if not key:
        raise ValueError("EMERGENT_LLM_KEY not set")
    provider, model = ROUTING[task]["emergent"]
    chat = LlmChat(api_key=key, session_id=session_id,
                   system_message=system).with_model(provider, model)
    resp = await chat.send_message(UserMessage(text=user))
    return resp if isinstance(resp, str) else str(resp)


async def _call_anthropic(system, user):
    import anthropic
    from config import settings

    key = settings.ANTHROPIC_API_KEY or ""
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=key)
    msg = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


async def _call_openai(system, user):
    from openai import AsyncOpenAI
    from config import settings

    key = settings.OPENAI_API_KEY or ""
    if not key:
        raise ValueError("OPENAI_API_KEY not set")
    client = AsyncOpenAI(api_key=key)
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


async def _call_gemini(system, user):
    import google.generativeai as genai
    from config import settings

    key = settings.GEMINI_API_KEY or ""
    if not key:
        raise ValueError("GEMINI_API_KEY not set")
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp", system_instruction=system)
    resp = await model.generate_content_async(user)
    return resp.text


FALLBACK_CHAIN = {
    "reasoning":  [_call_anthropic, _call_openai, _call_gemini],
    "fast":       [_call_gemini,    _call_anthropic, _call_openai],
    "structured": [_call_openai,    _call_anthropic, _call_gemini],
}


async def _call_direct(task, system, user):
    last = None
    for fn in FALLBACK_CHAIN.get(task, FALLBACK_CHAIN["reasoning"]):
        fn_name = fn.__name__
        if _cb.is_open(fn_name):
            logger.info("Circuit open — skipping %s", fn_name)
            continue
        try:
            logger.info("LLM direct fallback: %s", fn_name)
            result = await fn(system, user)
            _cb.record(fn_name, True)
            return result
        except Exception as ex:
            last = ex
            _cb.record(fn_name, False)
            logger.warning("LLM %s failed: %s", fn_name, ex)
    raise RuntimeError(f"All LLM providers failed: {last}")


async def llm_call(*, task: TaskType, system: str, user: str,
                   session_id: str, json_mode: bool = False) -> str:
    """Primary → Emergent. Fallback → direct APIs (circuit-breaker protected)."""
    emergent_err = None
    try:
        from config import settings as _s
        _timeout = _s.LLM_TIMEOUT_S
    except Exception:
        _timeout = 45
    try:
        result = await asyncio.wait_for(
            _call_emergent(task, system, user, session_id),
            timeout=_timeout,
        )
        _cb.record("emergent", True)
        return result
    except Exception as ex:
        emergent_err = ex
        _cb.record("emergent", False)
        logger.warning("Emergent failed (task=%s): %s — trying direct fallback", task, ex)
    try:
        return await _call_direct(task, system, user)
    except Exception as fallback_err:
        logger.error("All LLM providers failed (task=%s): %s", task, fallback_err)
        raise RuntimeError(f"LLM unavailable. Primary: {emergent_err}. Fallback: {fallback_err}")


def parse_json_loose(text: str) -> dict:
    """Deprecated: use parse_llm_json from llm_schemas instead."""
    from llm_schemas import parse_llm_json
    return parse_llm_json(text)


async def llm_health_check() -> dict:
    import asyncio
    results = {}
    try:
        # Timeout protection — readiness check must be fast (2 sec max)
        resp = await asyncio.wait_for(
            llm_call(task="fast", system="Reply OK", user="ping",
                     session_id="health_check"),
            timeout=2.0
        )
        results["emergent"] = "ok" if resp else "empty"
    except asyncio.TimeoutError:
        results["emergent"] = "timeout"
    except Exception as ex:
        results["emergent"] = f"error:{str(ex)[:60]}"
    return {
        "providers": results,
        "circuit_breakers": _cb.status(),
        "any_available": any(v == "ok" for v in results.values()),
    }
