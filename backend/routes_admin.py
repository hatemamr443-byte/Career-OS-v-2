"""
Career OS — Admin & Observability Routes.

Internal routes for monitoring the health and intelligence of the
system. NOT exposed publicly — requires admin token from env.

Endpoints:
  GET  /admin/telemetry          — AI call stats by feature + latency
  GET  /admin/event-bus          — Bus stats + recent events
  GET  /admin/circuit-breakers   — LLM provider circuit breaker state
  POST /admin/outbox/replay      — Replay failed events from outbox
  GET  /admin/memory/{user_id}   — Inspect a user's career memory
  GET  /admin/system             — Overall system health snapshot
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Header
from db import db as mongo_db, career_events
from event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", os.environ.get("CRON_TOKEN", ""))


def _require_admin(x_admin_token: str = Header(default="")):
    if not _ADMIN_TOKEN or x_admin_token != _ADMIN_TOKEN:
        raise HTTPException(403, "Admin token required")


# ── Telemetry ─────────────────────────────────────────────────────

@router.get("/telemetry")
async def telemetry_summary(
    hours: int = 24,
    _: None = None,
    x_admin_token: str = Header(default=""),
):
    _require_admin(x_admin_token)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": "$feature",
            "total_calls":   {"$sum": 1},
            "success_calls": {"$sum": {"$cond": ["$success", 1, 0]}},
            "error_calls":   {"$sum": {"$cond": ["$success", 0, 1]}},
            "avg_latency_ms": {"$avg": "$latency_ms"},
            "p95_latency_ms": {"$percentile": {"input": "$latency_ms", "p": [0.95], "method": "approximate"}},
            "total_chars":   {"$sum": "$output_chars"},
            "unique_users":  {"$addToSet": "$user_id"},
        }},
        {"$sort": {"total_calls": -1}},
    ]

    try:
        rows = await mongo_db.ai_telemetry.aggregate(pipeline).to_list(50)
        for r in rows:
            r["unique_users"] = len(r.get("unique_users", []))
            r["feature"] = r.pop("_id")
            r["error_rate"] = round(r["error_calls"] / max(r["total_calls"], 1), 3)
            if isinstance(r.get("p95_latency_ms"), list):
                r["p95_latency_ms"] = r["p95_latency_ms"][0] if r["p95_latency_ms"] else None
    except Exception:
        # Fallback for MongoDB < 7 (no $percentile)
        pipeline[1]["$group"].pop("p95_latency_ms", None)
        rows = await mongo_db.ai_telemetry.aggregate(pipeline).to_list(50)
        for r in rows:
            r["unique_users"] = len(r.get("unique_users", []))
            r["feature"] = r.pop("_id")
            r["error_rate"] = round(r["error_calls"] / max(r["total_calls"], 1), 3)

    return {
        "period_hours": hours,
        "since": since,
        "features": rows,
        "total_calls": sum(r["total_calls"] for r in rows),
    }


# ── Event Bus ─────────────────────────────────────────────────────

@router.get("/event-bus")
async def event_bus_stats(x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)
    return {
        "stats":  event_bus.stats(),
        "recent": event_bus.recent(20),
    }


# ── Circuit Breakers ──────────────────────────────────────────────

def _get_cb_status() -> dict:
    """Safe accessor for circuit breaker state — uses public API."""
    try:
        from llm_service import _cb  # noqa: PLC0415
        return _cb.status()
    except Exception:
        return {"error": "circuit breaker state unavailable"}


@router.get("/circuit-breakers")
async def circuit_breaker_status(x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)
    return {"circuit_breakers": _get_cb_status()}


# ── Outbox Replay ─────────────────────────────────────────────────

@router.post("/outbox/replay")
async def replay_outbox(
    payload: dict | None = None,
    x_admin_token: str = Header(default=""),
):
    """
    Replay events from events_outbox where delivered=False.

    Why: if a subscriber failed during initial dispatch, the event
    is still in the outbox. This endpoint re-dispatches it so
    cross-feature workflows don't silently drop.

    Idempotent: subscribers should handle duplicate events gracefully.
    """
    _require_admin(x_admin_token)
    limit = int((payload or {}).get("limit", 50))
    event_filter = (payload or {}).get("event_type")

    query: dict = {"delivered": False}
    if event_filter:
        query["event_type"] = event_filter

    pending = await mongo_db.events_outbox.find(
        query, {"_id": 1, "user_id": 1, "event_type": 1, "data": 1}
    ).sort("created_at", 1).limit(limit).to_list(limit)

    replayed, failed = 0, 0
    for ev in pending:
        try:
            # Re-publish through the public bus API — idempotent by design
            import asyncio  # noqa: PLC0415
            await asyncio.gather(
                event_bus.publish(ev["event_type"], ev["user_id"], ev["data"]),
                return_exceptions=True,
            )
            await mongo_db.events_outbox.update_one(
                {"_id": ev["_id"]},
                {"$set": {"delivered": True, "replayed_at": datetime.now(timezone.utc).isoformat()}},
            )
            replayed += 1
        except Exception as ex:
            logger.warning("Outbox replay failed for event %s: %s", ev.get("event_type"), ex)
            failed += 1

    return {"replayed": replayed, "failed": failed, "pending_total": len(pending)}


# ── Career Memory Inspector ───────────────────────────────────────

@router.get("/memory/{user_id}")
async def inspect_memory(user_id: str, x_admin_token: str = Header(default="")):
    """Inspect a user's career memory — useful for debugging orchestrator context."""
    _require_admin(x_admin_token)
    from memory_service import MemoryService
    from career_intelligence import CareerIntelligence

    mem = MemoryService(user_id)
    snippets = await mem.recall(k=15)
    prompt_block = await mem.recall_prompt_block(k=10)

    ci = CareerIntelligence(user_id)
    signals = await ci.cross_feature_signals()
    ctx = await ci.get_context(depth="full")

    recent_events = await career_events.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)

    return {
        "user_id":       user_id,
        "memory_snippets": snippets,
        "prompt_block":  prompt_block,
        "cross_feature_signals": signals,
        "career_context": ctx,
        "recent_career_events": recent_events,
    }


# ── System Snapshot ───────────────────────────────────────────────

@router.get("/system")
async def system_snapshot(x_admin_token: str = Header(default="")):
    """Full system health: DB, LLM, bus, collections, indexes."""
    _require_admin(x_admin_token)
    from llm_service import llm_health_check

    # DB stats
    try:
        await mongo_db.command("ping")
        db_ok = True
        collection_counts = {}
        for coll in ["users", "jobs", "applications", "career_events",
                     "ai_telemetry", "events_outbox"]:
            try:
                collection_counts[coll] = await mongo_db[coll].count_documents({})
            except Exception:
                collection_counts[coll] = -1
    except Exception as ex:
        db_ok = False
        collection_counts = {"error": str(ex)}

    # LLM health
    try:
        llm_health = await llm_health_check()
    except Exception as ex:
        llm_health = {"error": str(ex)}

    # Outbox pending
    try:
        outbox_pending = await mongo_db.events_outbox.count_documents({"delivered": False})
    except Exception:
        outbox_pending = -1

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": {"ok": db_ok, "collections": collection_counts},
        "llm": llm_health,
        "event_bus": event_bus.stats(),
        "circuit_breakers": _get_cb_status(),
        "outbox_pending": outbox_pending,
        "working_memory": __import__("working_memory").working_memory.stats(),
        "langfuse": __import__("langfuse_tracer").tracer.status(),
        "firecrawl": __import__("firecrawl_adapter").firecrawl.status(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "version": "2.1.0",
    }
