"""
Memory Consolidation Worker — background job that synthesises
career events into durable AI notes stored in career_graph.

Triggered daily via /api/internal/consolidate-memory cron endpoint.
Idempotent: skips users updated in the last 7 days.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from db import db as mongo_db
from orchestrator import orchestrator

logger = logging.getLogger(__name__)

CONSOLIDATION_INTERVAL_DAYS = 7
MAX_USERS_PER_RUN = 20


async def consolidate_user_memory(user_id: str) -> str | None:
    events = await mongo_db.career_events.find(
        {"user_id": user_id},
        {"_id": 0, "event_type": 1, "data": 1, "created_at": 1}
    ).sort("created_at", -1).limit(50).to_list(50)

    activities = await mongo_db.activity_logs.find(
        {"user_id": user_id},
        {"_id": 0, "event_type": 1, "title": 1, "created_at": 1}
    ).sort("created_at", -1).limit(50).to_list(50)

    if not events and not activities:
        return None

    def _fmt(ev: dict) -> str:
        et = ev.get("event_type", "")
        data = ev.get("data") or {}
        ts = (ev.get("created_at") or "")[:10]
        parts = [f"[{ts}] {et.replace('_', ' ')}"]
        for k in ["job_title", "company", "role", "score", "title"]:
            if data.get(k):
                parts.append(str(data[k]))
        return " — ".join(parts)

    event_lines    = [_fmt(e) for e in events[:30]]
    activity_lines = [f"[{(a.get('created_at',''))[:10]}] {a.get('title','')}" for a in activities[:20]]
    event_summary  = "\n".join(event_lines + activity_lines)

    try:
        notes = await orchestrator.run(
            user_id=user_id,
            feature="memory_consolidation",
            task="fast",
            feature_prompt=(
                "You are Career OS's Memory Synthesizer. "
                "Analyse career events and write a concise intelligence note "
                "for future AI system prompts. Focus on: patterns, tendencies, "
                "progress, blind spots, strategic observations. "
                "Max 200 words. Second person. Facts only. No fluff."
            ),
            user_message=f"Career events (last 90 days):\n{event_summary}",
            session_id=f"memconsolidate_{user_id}",
            context_depth="minimal",
        )
        if notes:
            from career_intelligence import CareerIntelligence
            await CareerIntelligence(user_id).update_ai_notes(notes.strip())
            logger.info("Memory consolidated user=%s (%d chars)", user_id, len(notes))
        return notes
    except Exception as ex:
        logger.warning("Consolidation failed user=%s: %s", user_id, ex)
        return None


async def run_consolidation_batch() -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CONSOLIDATION_INTERVAL_DAYS)).isoformat()
    stale = await mongo_db.career_graph.find(
        {"$or": [{"notes_updated_at": {"$lt": cutoff}}, {"notes_updated_at": {"$exists": False}}]},
        {"user_id": 1, "_id": 0}
    ).limit(MAX_USERS_PER_RUN).to_list(MAX_USERS_PER_RUN)

    processed = skipped = 0
    for doc in stale:
        uid = doc.get("user_id")
        if not uid:
            continue
        n = await mongo_db.career_events.count_documents({"user_id": uid})
        if n < 3:
            skipped += 1
            continue
        result = await consolidate_user_memory(uid)
        processed += 1 if result else 0
        skipped   += 0 if result else 1

    logger.info("Consolidation batch: processed=%d skipped=%d", processed, skipped)
    return {"processed": processed, "skipped": skipped, "total": len(stale)}
