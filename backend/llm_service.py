"""LLM Router: routes tasks to Claude (reasoning) or Gemini (fast/bulk)."""
import os
import json
import re
from typing import Literal
from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

TaskType = Literal["reasoning", "fast", "structured"]


def _model_for(task: TaskType):
    if task == "fast":
        return ("gemini", "gemini-3-flash-preview")
    if task == "structured":
        return ("openai", "gpt-5.1")
    return ("anthropic", "claude-sonnet-4-5-20250929")


async def llm_call(
    *,
    task: TaskType,
    system: str,
    user: str,
    session_id: str,
    json_mode: bool = False,
) -> str:
    provider, model = _model_for(task)
    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model(provider, model)
    msg = UserMessage(text=user)
    resp = await chat.send_message(msg)
    return resp if isinstance(resp, str) else str(resp)


def parse_json_loose(text: str) -> dict:
    """Extract JSON from LLM text response, handling code fences."""
    if not text:
        return {}
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip code fence
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # first {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}
