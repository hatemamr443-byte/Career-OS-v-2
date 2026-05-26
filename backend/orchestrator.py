"""
Career OS — Orchestrator.

The unified entry point for AI features. Replaces direct `llm_call()` usage
over time. Provides:

  1. Shared persona / tone (one voice across the product).
  2. Memory injection (relevant prior events).
  3. Career context injection (CareerIntelligence).
  4. Provider routing (delegates to llm_service.llm_call).
  5. Telemetry (records every call to `ai_telemetry`).
  6. Event publication (broadcasts completion via event_bus).

Backwards-compat: existing routes can keep calling `llm_call()` directly.
New routes — and migrated routes — should call `orchestrator.run()`.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from typing import Literal

from db import db as mongo_db
from llm_service import llm_call, parse_json_loose
from career_intelligence import CareerIntelligence
from memory_service import MemoryService
from event_bus import event_bus
from working_memory import working_memory
from langfuse_tracer import tracer as lf_tracer
from episodic_memory import record_from_event, episodes_prompt_block

logger = logging.getLogger(__name__)
ai_telemetry = mongo_db.ai_telemetry

TaskType = Literal["reasoning", "fast", "structured"]

# ── The unified Career OS voice ────────────────────────────────────
SYSTEM_PERSONA = (
    "You are Career OS — a senior career strategist embedded in this user's "
    "professional life. You speak calmly, specifically, and strategically. "
    "You never give generic advice. You always anchor your reasoning in what "
    "you know about this user (their history, skills, preferences, salary "
    "expectations). You optimize for long-term career capital, not short-term "
    "wins. When you are uncertain, you say so. You return ONLY what the "
    "task asks for — no preambles, no apologies, no filler."
)


class Orchestrator:
    """Single intelligent entry point for every AI feature."""

    async def build_system_prompt(
        self,
        user_id: str,
        feature_prompt: str,
        *,
        memory_k: int = 6,
        context_depth: str = "standard",
    ) -> str:
        """Compose: PERSONA + MEMORY + CAREER CONTEXT + FEATURE INSTRUCTIONS."""
        parts: list[str] = [SYSTEM_PERSONA]

        # Memory recall
        try:
            mem = MemoryService(user_id)
            mem_block = await mem.recall_prompt_block(k=memory_k)
            if mem_block:
                parts.append(mem_block)
        except Exception as ex:
            logger.warning("Memory recall failed for user=%s: %s", user_id, ex)

        # Career context
        try:
            ci = CareerIntelligence(user_id)
            ctx_block = await ci.get_context_prompt(depth=context_depth)
            if ctx_block:
                parts.append(ctx_block)
        except Exception as ex:
            logger.warning("Career context failed for user=%s: %s", user_id, ex)

        # Episodic memory — key career milestones and decisions
        try:
            ep_block = await episodes_prompt_block(user_id, k=3)
            if ep_block:
                parts.append(ep_block)
        except Exception as ex:
            logger.debug("Episodic memory failed: %s", ex)

        # Working memory — active session context
        try:
            wm_block = working_memory.get_prompt_block(user_id)
            if wm_block:
                parts.append(wm_block)
        except Exception as ex:
            logger.debug("Working memory failed: %s", ex)

        # The feature-specific instructions go last (closest to user message).
        parts.append(feature_prompt)
        return "\n\n".join(parts)

    async def run(
        self,
        *,
        user_id: str,
        feature: str,
        task: TaskType,
        feature_prompt: str,
        user_message: str,
        session_id: str | None = None,
        memory_k: int = 6,
        context_depth: str = "standard",
        publish_event: str | None = None,
        event_payload: dict | None = None,
    ) -> str:
        """End-to-end AI call. Returns raw LLM text.

        - Builds the unified system prompt.
        - Calls llm_service.llm_call with task-aware routing.
        - Records telemetry.
        - Optionally publishes a completion event.
        """
        sid = session_id or f"{feature}_{user_id}_{int(time.time())}"
        system = await self.build_system_prompt(
            user_id, feature_prompt,
            memory_k=memory_k, context_depth=context_depth,
        )

        start = time.perf_counter()
        success = True
        error: str | None = None
        text = ""

        try:
            async with lf_tracer.span(
                user_id, feature, task,
                system_prompt=system[:400], user_message=user_message[:300],
            ) as _lf_span:
                text = await llm_call(
                    task=task, system=system, user=user_message, session_id=sid,
                )
                _lf_span.set_output(text[:300] if text else "")
            return text
        except Exception as ex:
            success = False
            error = str(ex)[:300]
            logger.error("Orchestrator.run failed feature=%s: %s", feature, ex)
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            # Fire-and-forget telemetry; never let it break the request.
            try:
                await ai_telemetry.insert_one({
                    "user_id":    user_id,
                    "feature":    feature,
                    "task":       task,
                    "latency_ms": latency_ms,
                    "success":    success,
                    "error":      error,
                    "session_id": sid,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "output_chars": len(text or ""),
                })
            except Exception as tex:
                logger.warning("Telemetry insert failed: %s", tex)

            # Publish completion event if requested.
            if success and publish_event:
                try:
                    await event_bus.publish(
                        publish_event, user_id, event_payload or {},
                    )
                except Exception as pex:
                    logger.warning("Event publish failed: %s", pex)

    @staticmethod
    def parse_json(text: str) -> dict:
        return parse_json_loose(text)


# Singleton
orchestrator = Orchestrator()


# ── Default subscribers wiring (cross-feature workflows) ───────────
# Lightweight handlers that demonstrate the orchestration value. They use
# CareerIntelligence to keep the graph fresh from any bus event.

async def _graph_record_handler(user_id: str, payload: dict) -> None:
    """Generic: forward published events into the CareerIntelligence graph."""
    et = payload.get("_event_type")  # optional
    if not et:
        return
    try:
        await CareerIntelligence(user_id).record_event(et, payload)
    except Exception as ex:
        logger.debug("graph record skipped: %s", ex)


# We intentionally do NOT auto-subscribe in module import to keep startup
# deterministic. Subscribers are registered explicitly in `wire_subscribers()`
# which server.py calls on startup.

def wire_subscribers() -> None:
    """Register default cross-feature subscribers. Idempotent.

    Each subscriber implements a specific workflow handoff requested in
    the P1 Brain Activation. Failures are isolated by the bus.
    """
    interview_prep_context = mongo_db.interview_prep_context
    salary_comparison      = mongo_db.salary_comparison
    cv_tailor_hints        = mongo_db.cv_tailor_hints

    # ── Career graph hydration (all material events) ──────────────
    async def on_job_rejected(user_id: str, data: dict) -> None:
        await CareerIntelligence(user_id).record_event("job_rejected", data)
        # Trigger skill-gap awareness: record an intent flag so the next
        # Dashboard load can show "We noticed 3 rejections recently — review
        # your skill gaps". The actual analysis runs on user pull.
        await mongo_db.workflow_hints.update_one(
            {"user_id": user_id, "kind": "skill_gap_review"},
            {"$set": {
                "user_id": user_id, "kind": "skill_gap_review",
                "reason":  "rejection_pattern_detected",
                "trigger_event": data,
                "active":   True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

    async def on_interview_completed(user_id: str, data: dict) -> None:
        await CareerIntelligence(user_id).record_event("interview_completed", data)

    async def on_offer_received(user_id: str, data: dict) -> None:
        await CareerIntelligence(user_id).record_event("offer_received", data)
        # Seed salary-comparison context so the Salary page can show
        # "How does this offer compare to market?" without a fresh AI call.
        await salary_comparison.update_one(
            {"user_id": user_id, "company": data.get("company")},
            {"$set": {
                "user_id":  user_id,
                "company":  data.get("company"),
                "job_id":   data.get("job_id"),
                "salary":   data.get("salary"),
                "needs_comparison": True,
                "seeded_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

    async def on_job_applied(user_id: str, data: dict) -> None:
        # Memory only — already heavily covered by activity_logs
        await mongo_db.career_events.insert_one({
            "user_id": user_id, "event_type": "job_applied",
            "data": data, "created_at": datetime.now(timezone.utc).isoformat(),
        }) if False else None  # career_events already written by bus.publish

    async def on_recruiter_reachout(user_id: str, data: dict) -> None:
        # Seed interview-prep context so InterviewPrep page can pre-fill
        # company research the moment the user opens it.
        await interview_prep_context.update_one(
            {"user_id": user_id, "from_addr": data.get("from_addr", "")},
            {"$set": {
                "user_id":      user_id,
                "from_name":    data.get("from_name"),
                "from_addr":    data.get("from_addr"),
                "subject":      data.get("subject"),
                "intent":       data.get("intent"),
                "next_steps":   data.get("next_steps"),
                "seeded_at":    datetime.now(timezone.utc).isoformat(),
                "consumed":     False,
            }},
            upsert=True,
        )

    async def on_bookmark_added(user_id: str, data: dict) -> None:
        # CV tailor pre-warm: stash a hint so when the user opens CV Tailor
        # we can suggest "Tailor for the role you just saved at Notion?"
        await cv_tailor_hints.update_one(
            {"user_id": user_id, "job_id": data.get("job_id")},
            {"$set": {
                "user_id":   user_id,
                "job_id":    data.get("job_id"),
                "job_title": data.get("job_title"),
                "company":   data.get("company"),
                "hint":      "bookmark_added",
                "active":    True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

    # Wire all subscribers
    event_bus.subscribe("job_rejected",        on_job_rejected)
    event_bus.subscribe("interview_completed", on_interview_completed)
    event_bus.subscribe("offer_received",      on_offer_received)
    event_bus.subscribe("job_applied",         on_job_applied)
    event_bus.subscribe("recruiter_reachout",  on_recruiter_reachout)
    event_bus.subscribe("bookmark_added",      on_bookmark_added)

    # Episodic memory — auto-record high-signal career episodes
    async def _record_episode(user_id: str, data: dict, evt: str) -> None:
        try:
            await record_from_event(user_id, evt, data)
        except Exception as ex:
            logger.debug("Episodic record failed evt=%s: %s", evt, ex)

    for _evt in ("offer_received", "job_rejected", "interview_completed", "cv_tailored"):
        event_bus.subscribe(_evt, lambda u, d, e=_evt: _record_episode(u, d, e))
