"""
Career OS — Episodic Memory.

Stores high-signal career episodes: milestones, decisions, failures,
breakthroughs. Unlike raw career_events (individual atomic events),
episodes are synthesised narratives — compressed, meaningful, durable.

Episode types:
  milestone   — offer received, job started, promotion, course completed
  decision    — strategic choice (accepted/rejected offer, pivoted direction)
  failure     — rejection streak, botched interview, missed opportunity
  session     — important AI coaching conversation summary
  insight     — pattern AI detected and surfaced to user

Storage: episodes MongoDB collection (lightweight, queryable).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from db import db as mongo_db
from models import new_id

logger = logging.getLogger(__name__)

EPISODE_TYPES = frozenset({"milestone", "decision", "failure", "session", "insight"})


async def record_episode(
    user_id: str,
    episode_type: str,
    title: str,
    summary: str,
    *,
    importance: float = 0.5,   # 0.0–1.0
    tags: list[str] | None = None,
    linked_event_ids: list[str] | None = None,
    metadata: dict | None = None,
) -> str:
    """
    Store an episode. Returns episode_id.

    Deduplication: within 1 hour, same user + title = update not insert.
    """
    if episode_type not in EPISODE_TYPES:
        episode_type = "session"

    importance = max(0.0, min(1.0, importance))
    now = datetime.now(timezone.utc)
    one_hour_ago = now.isoformat()[:13]  # "2026-05-01T14" prefix match

    # Dedup check — same title in the last hour
    existing = await mongo_db.episodes.find_one({
        "user_id": user_id,
        "title": title,
        "created_at": {"$gte": one_hour_ago},
    })

    if existing:
        await mongo_db.episodes.update_one(
            {"episode_id": existing["episode_id"]},
            {"$set": {
                "summary": summary,
                "importance": max(existing.get("importance", 0), importance),
                "updated_at": now.isoformat(),
            }}
        )
        return existing["episode_id"]

    episode_id = new_id("ep")
    doc = {
        "episode_id":        episode_id,
        "user_id":           user_id,
        "episode_type":      episode_type,
        "title":             title,
        "summary":           summary[:800],
        "importance":        importance,
        "tags":              tags or [],
        "linked_event_ids":  linked_event_ids or [],
        "metadata":          metadata or {},
        "created_at":        now.isoformat(),
        "updated_at":        now.isoformat(),
    }
    await mongo_db.episodes.insert_one(doc)
    logger.info("Episode recorded user=%s type=%s title=%s", user_id, episode_type, title[:40])
    return episode_id


async def recall_episodes(
    user_id: str,
    *,
    episode_type: str | None = None,
    k: int = 5,
    min_importance: float = 0.3,
) -> list[dict]:
    """Return top-k episodes sorted by importance × recency."""
    query: dict = {"user_id": user_id, "importance": {"$gte": min_importance}}
    if episode_type:
        query["episode_type"] = episode_type

    docs = await mongo_db.episodes.find(
        query, {"_id": 0}
    ).sort([("importance", -1), ("created_at", -1)]).limit(k * 2).to_list(k * 2)

    # Re-rank by importance × recency score
    now = datetime.now(timezone.utc)
    def score(ep: dict) -> float:
        imp = ep.get("importance", 0.5)
        try:
            ts = datetime.fromisoformat(ep["created_at"].replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (now - ts).total_seconds() / 86400
            recency = max(0.1, 1.0 - age_days / 365)
        except Exception:
            recency = 0.5
        return imp * recency

    docs.sort(key=score, reverse=True)
    return docs[:k]


async def episodes_prompt_block(user_id: str, k: int = 3) -> str:
    """Format top episodes as a system prompt block."""
    episodes = await recall_episodes(user_id, k=k, min_importance=0.4)
    if not episodes:
        return ""
    lines = []
    for ep in episodes:
        date = ep.get("created_at", "")[:10]
        etype = ep.get("episode_type", "?")
        title = ep.get("title", "")
        summary = ep.get("summary", "")[:120]
        lines.append(f"  [{date}] {etype.upper()}: {title} — {summary}")
    return "## Key Career Episodes\n" + "\n".join(lines)


# ── Auto-record from known events ─────────────────────────────────

async def record_from_event(
    user_id: str,
    event_type: str,
    data: dict,
) -> None:
    """
    Called by wire_subscribers — automatically creates episodes from
    high-signal career events without manual intervention.
    """
    title = summary = ""
    importance = 0.4
    etype = "session"

    if event_type == "offer_received":
        company = data.get("company", "")
        salary = data.get("salary", "")
        title = f"Offer received from {company}"
        summary = f"Received job offer from {company}. Salary: {salary or 'undisclosed'}."
        importance = 0.95
        etype = "milestone"

    elif event_type == "job_rejected":
        company = data.get("company", "")
        reason = data.get("rejection_reason", "")
        title = f"Rejected by {company}"
        summary = f"Application rejected by {company}. {('Reason: ' + reason) if reason else 'No reason given.'}"
        importance = 0.55
        etype = "failure"

    elif event_type == "interview_completed":
        company = data.get("company") or data.get("job_title", "")
        avg_score = data.get("average_score")
        title = f"Interview at {company}"
        summary = f"Completed interview at {company}." + (f" Avg score: {avg_score}/10." if avg_score else "")
        importance = 0.70
        etype = "milestone" if avg_score and float(avg_score) >= 7 else "session"

    elif event_type == "cv_tailored":
        job_title = data.get("job_title", "role")
        title = f"CV tailored for {job_title}"
        summary = f"CV tailored and optimised for {job_title}."
        importance = 0.35
        etype = "session"

    if title:
        await record_episode(
            user_id, etype, title, summary,
            importance=importance,
            tags=[event_type],
            metadata=data,
        )
