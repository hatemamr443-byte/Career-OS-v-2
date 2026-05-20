"""
Career OS — Memory Service.

Reads `career_events` and returns *scored, ranked* memory snippets for
injection into LLM system prompts. This is what makes Career OS feel
*persistent and contextual* rather than stateless.

Scoring formula:
    score(event) = WEIGHT[event_type] * exp(-age_days / HALF_LIFE[event_type])

The result is a small list of compact strings the LLM can read in O(seconds).

Usage:
    from memory_service import MemoryService

    mem = MemoryService(user_id)
    snippets = await mem.recall(k=8)
    # → ["[2d ago] interviewed at Stripe (avg score 7.2)",
    #    "[5d ago] CV tailored for Senior PM at Notion",
    #    ...]
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Iterable

from db import career_events, activity_logs

# Event weights and half-lives (in days). Tunable, human-readable.
MEMORY_WEIGHTS: dict[str, tuple[float, float]] = {
    # event_type:               (weight, half_life_days)
    "offer_received":           (100, 365),
    "interview_completed":      (60,   90),
    "job_rejected":             (40,   60),
    "cv_tailored":              (30,   30),
    "salary_research":          (25,   30),
    "decision_strategic_plan":  (25,   45),
    "job_applied":              (20,   21),
    "bookmark":                 (10,   14),
    "match_analyzed":           (8,    10),
    "view":                     (3,     3),
    # Activity-log derived events
    "cv_uploaded":              (15,   30),
    "profile_updated":          (5,    14),
    "coach_chat":               (4,    7),
    "company_research":         (8,    14),
    "ats_scored":               (6,    10),
}
DEFAULT_WEIGHT = (5.0, 14.0)


def _score(event_type: str, age_days: float) -> float:
    w, h = MEMORY_WEIGHTS.get(event_type, DEFAULT_WEIGHT)
    return w * math.exp(-age_days / max(h, 0.001))


def _format_snippet(event: dict, age_days: float) -> str:
    et = event.get("event_type", "event")
    data = event.get("data", {}) or {}
    if age_days < 1:
        age = "today"
    elif age_days < 2:
        age = "yesterday"
    elif age_days < 30:
        age = f"{int(age_days)}d ago"
    elif age_days < 365:
        age = f"{int(age_days / 30)}mo ago"
    else:
        age = f"{age_days / 365:.1f}y ago"

    detail = ""
    if et == "interview_completed":
        score = data.get("average_score")
        company = data.get("company") or data.get("job_title", "")
        detail = f"interviewed{f' at {company}' if company else ''}" + (
            f" (avg score {score})" if score is not None else ""
        )
    elif et == "job_rejected":
        company = data.get("company", "")
        title = data.get("job_title", "")
        detail = f"rejection: {title}{f' at {company}' if company else ''}".strip()
    elif et == "offer_received":
        company = data.get("company", "")
        salary = data.get("salary")
        detail = f"offer{f' from {company}' if company else ''}" + (
            f" — {salary}" if salary else ""
        )
    elif et == "cv_tailored":
        title = data.get("job_title") or data.get("title", "")
        detail = f"CV tailored{f' for {title}' if title else ''}"
    elif et == "job_applied":
        title = data.get("job_title", "")
        company = data.get("company", "")
        detail = f"applied{f' to {title}' if title else ''}{f' @ {company}' if company else ''}"
    elif et == "salary_research":
        role = data.get("role", "")
        detail = f"salary researched{f' for {role}' if role else ''}"
    elif et == "decision_strategic_plan":
        detail = "generated 90-day strategic plan"
    elif et == "match_analyzed":
        score = data.get("score")
        title = data.get("title", "")
        detail = f"match {score or '?'}/100" + (f" — {title}" if title else "")
    else:
        # Generic
        detail = et.replace("_", " ")
    return f"[{age}] {detail}".strip()


class MemoryService:
    """Per-user career memory retrieval."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def recall(self, k: int = 8, since_days: int = 365) -> list[str]:
        """Return top-K most relevant memory snippets from career events + activity logs."""
        now = datetime.now(timezone.utc)

        # Pull career_events (primary) AND activity_logs (behavioral enrichment)
        # Merge both streams — scoring is cheap, breadth is valuable.
        scored: list[tuple[float, str]] = []

        async def _score_cursor(cursor) -> None:
            async for ev in cursor:
                created = ev.get("created_at")
                if isinstance(created, str):
                    try:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except Exception:
                        continue
                elif isinstance(created, datetime):
                    created_dt = created
                else:
                    continue
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                age_days = max((now - created_dt).total_seconds() / 86400, 0.0)
                if age_days > since_days:
                    continue
                s = _score(ev.get("event_type", ""), age_days)
                if s > 0:
                    scored.append((s, _format_snippet(ev, age_days)))

        career_cursor = career_events.find(
            {"user_id": self.user_id},
            {"_id": 0, "event_type": 1, "data": 1, "created_at": 1},
        ).sort("created_at", -1).limit(200)

        # Also pull activity_logs to capture CV uploads, profile changes, coach chats
        activity_cursor = activity_logs.find(
            {"user_id": self.user_id},
            {"_id": 0, "event_type": 1, "metadata": 1, "created_at": 1},
        ).sort("created_at", -1).limit(100)

        await _score_cursor(career_cursor)
        # Remap activity_logs format to match career_events schema
        async for ev in activity_cursor:
            ev["data"] = ev.pop("metadata", {})
            await _score_cursor.__wrapped__(ev) if hasattr(_score_cursor, '__wrapped__') else None

        scored.sort(key=lambda x: -x[0])
        return [snippet for _, snippet in scored[:k]]

    async def _score_one(self, ev: dict, now: datetime, since_days: float) -> tuple[float, str] | None:
        created = ev.get("created_at")
        if isinstance(created, str):
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except Exception:
                return None
        elif isinstance(created, datetime):
            created_dt = created
        else:
            return None
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        age_days = max((now - created_dt).total_seconds() / 86400, 0.0)
        if age_days > since_days:
            return None
        s = _score(ev.get("event_type", ""), age_days)
        return (s, _format_snippet(ev, age_days)) if s > 0 else None

    async def recall_v2(self, k: int = 8, since_days: int = 365) -> list[str]:
        """Improved recall: merges career_events + activity_logs."""
        now = datetime.now(timezone.utc)
        scored: list[tuple[float, str]] = []

        # career_events stream
        async for ev in career_events.find(
            {"user_id": self.user_id},
            {"_id": 0, "event_type": 1, "data": 1, "created_at": 1},
        ).sort("created_at", -1).limit(200):
            result = await self._score_one(ev, now, since_days)
            if result:
                scored.append(result)

        # activity_logs stream (remap metadata → data)
        async for ev in activity_logs.find(
            {"user_id": self.user_id},
            {"_id": 0, "event_type": 1, "metadata": 1, "created_at": 1},
        ).sort("created_at", -1).limit(100):
            ev["data"] = ev.pop("metadata", {})
            result = await self._score_one(ev, now, since_days)
            if result:
                scored.append(result)

        scored.sort(key=lambda x: -x[0])
        return [snippet for _, snippet in scored[:k]]

    async def _old_recall(self, k: int = 8, since_days: int = 365) -> list[str]:
        """Original recall (career_events only) — kept for reference."""
        now = datetime.now(timezone.utc)

        cursor = career_events.find(
            {"user_id": self.user_id},
            {"_id": 0, "event_type": 1, "data": 1, "created_at": 1},
        ).sort("created_at", -1).limit(200)

        scored: list[tuple[float, str]] = []
        async for ev in cursor:
            created = ev.get("created_at")
            if isinstance(created, str):
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except Exception:
                    continue
            elif isinstance(created, datetime):
                created_dt = created
            else:
                continue
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)

            age_days = max((now - created_dt).total_seconds() / 86400, 0.0)
            if age_days > since_days:
                continue

            s = _score(ev.get("event_type", ""), age_days)
            if s <= 0:
                continue
            scored.append((s, _format_snippet(ev, age_days)))

        scored.sort(key=lambda x: -x[0])
        return [snippet for _, snippet in scored[:k]]

    async def recall_prompt_block(self, k: int = 8) -> str:
        """Return memory formatted for LLM system prompt injection."""
        snippets = await self.recall(k=k)
        if not snippets:
            return ""
        return "## Career Memory (most relevant prior events)\n" + "\n".join(
            f"- {s}" for s in snippets
        )

    @staticmethod
    def event_types() -> Iterable[str]:
        return MEMORY_WEIGHTS.keys()
