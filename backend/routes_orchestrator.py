"""
Orchestrator HTTP routes — health + introspection + telemetry.

  GET  /api/orchestrator/health         — providers + memory + bus health
  GET  /api/orchestrator/recent-events  — recent bus events for current user
  GET  /api/orchestrator/memory         — preview of memory recall for me
  GET  /api/orchestrator/telemetry      — orchestration latency, provider
                                          mix, fallback rate, event throughput
                                          (current user only)
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from auth import get_current_user
from event_bus import event_bus
from memory_service import MemoryService
from llm_service import llm_health_check
from db import db as mongo_db
from insights_service import build_insights, dismiss_insight

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


@router.get("/insights")
async def insights(user=Depends(get_current_user)):
    """Active Brain Reveal cards for the current user.

    Returns a small list (≤5) of typed insights derived from the
    orchestration layer's outputs. No fresh AI inference — pure
    aggregation over workflow_hints / interview_prep_context /
    cv_tailor_hints / salary_comparison / cross-feature signals.
    """
    items = await build_insights(user["user_id"])
    return {"insights": items, "count": len(items)}


@router.post("/insights/{insight_id}/dismiss")
async def insights_dismiss(insight_id: str, user=Depends(get_current_user)):
    """Mark an insight as dismissed; cleanly retires the source state."""
    await dismiss_insight(user["user_id"], insight_id)
    return {"ok": True, "insight_id": insight_id}


@router.get("/health")
async def orchestrator_health():
    """Composite health: bus stats + LLM provider probe."""
    llm = await llm_health_check()
    return {"ok": True, "bus": event_bus.stats(), "llm": llm}


@router.get("/recent-events")
async def recent_events(user=Depends(get_current_user), limit: int = 20):
    """Recent in-memory bus events filtered for the current user."""
    items = [e for e in event_bus.recent(limit=limit)
             if e.get("user_id") == user["user_id"]]
    return {"events": items, "count": len(items)}


@router.get("/memory")
async def memory_preview(user=Depends(get_current_user), k: int = 10):
    """Preview of the scored memory the AI would receive for this user."""
    mem = MemoryService(user["user_id"])
    snippets = await mem.recall(k=k)
    return {"k": k, "snippets": snippets, "count": len(snippets)}


@router.get("/telemetry")
async def telemetry(user=Depends(get_current_user), days: int = 7):
    """Per-user orchestration telemetry over the last N days.

    Provides:
      - call counts by feature
      - latency p50 / p95 / max
      - success rate
      - memory snippet average (from recent recalls)
      - event throughput counts by type
    """
    uid = user["user_id"]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # AI telemetry rollup
    ai_col = mongo_db.ai_telemetry
    cursor = ai_col.find(
        {"user_id": uid, "created_at": {"$gte": since}},
        {"_id": 0, "feature": 1, "latency_ms": 1, "success": 1, "task": 1},
    ).limit(2000)

    latencies: list[int] = []
    by_feature: dict[str, dict] = {}
    by_task: dict[str, int] = {}
    success_count = 0
    total = 0
    async for row in cursor:
        total += 1
        lat = int(row.get("latency_ms") or 0)
        latencies.append(lat)
        f = row.get("feature", "?")
        t = row.get("task", "?")
        by_task[t] = by_task.get(t, 0) + 1
        bucket = by_feature.setdefault(f, {"calls": 0, "latency_sum": 0, "fails": 0})
        bucket["calls"] += 1
        bucket["latency_sum"] += lat
        if row.get("success"):
            success_count += 1
        else:
            bucket["fails"] += 1

    def _pct(arr: list[int], p: int) -> int:
        if not arr:
            return 0
        s = sorted(arr)
        idx = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
        return int(s[idx])

    for f, b in by_feature.items():
        b["avg_latency_ms"] = int(b["latency_sum"] / max(b["calls"], 1))
        b.pop("latency_sum", None)

    # Event throughput from career_events (durable) — best-effort
    event_throughput: dict[str, int] = {}
    try:
        cursor2 = mongo_db.career_events.find(
            {"user_id": uid, "created_at": {"$gte": since}},
            {"_id": 0, "event_type": 1},
        ).limit(5000)
        async for ev in cursor2:
            t = ev.get("event_type", "?")
            event_throughput[t] = event_throughput.get(t, 0) + 1
    except Exception:
        pass

    return {
        "window_days":      days,
        "total_ai_calls":   total,
        "success_rate":     round(100 * success_count / total, 1) if total else 0.0,
        "latency_ms":       {
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "max": max(latencies) if latencies else 0,
        },
        "by_feature":       by_feature,
        "by_task":          by_task,
        "event_throughput": event_throughput,
        "bus_global":       event_bus.stats(),
    }
