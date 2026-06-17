"""
Career OS — Memory API Routes.

Exposes the hybrid memory system (episodic + working) to the frontend.

GET  /api/memory/episodes          — list career episodes
GET  /api/memory/episodes/:id      — single episode
POST /api/memory/episodes          — manually record episode
DELETE /api/memory/episodes/:id    — delete episode
GET  /api/memory/working           — active session context
GET  /api/memory/stats             — memory system statistics
POST /api/memory/consolidate       — trigger memory consolidation
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from auth import get_current_user
from episodic_memory import record_episode, recall_episodes
from working_memory import working_memory
from db import db as mongo_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


# ── Episodes ──────────────────────────────────────────────────────

@router.get("/episodes")
async def list_episodes(
    episode_type: str | None = None,
    k: int = 20,
    min_importance: float = 0.0,
    user=Depends(get_current_user),
):
    """List user's career episodes ordered by importance × recency."""
    try:
        episodes = await recall_episodes(
            user["user_id"],
            episode_type=episode_type,
            k=k,
            min_importance=min_importance,
        )
        return {"episodes": episodes, "count": len(episodes)}
    except Exception as ex:
        logger.error("list_episodes failed user=%s: %s", user["user_id"], ex)
        raise HTTPException(500, "Failed to retrieve episodes.")


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: str, user=Depends(get_current_user)):
    doc = await mongo_db.episodes.find_one(
        {"episode_id": episode_id, "user_id": user["user_id"]},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Episode not found.")
    return doc


@router.post("/episodes")
async def create_episode(payload: dict, user=Depends(get_current_user)):
    """Manually record a career episode."""
    title = (payload.get("title") or "").strip()
    summary = (payload.get("summary") or "").strip()
    if not title or not summary:
        raise HTTPException(400, "title and summary required.")

    episode_id = await record_episode(
        user["user_id"],
        episode_type=payload.get("episode_type", "session"),
        title=title,
        summary=summary,
        importance=float(payload.get("importance", 0.5)),
        tags=payload.get("tags", []),
        metadata=payload.get("metadata", {}),
    )
    return {"episode_id": episode_id, "ok": True}


@router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: str, user=Depends(get_current_user)):
    r = await mongo_db.episodes.delete_one(
        {"episode_id": episode_id, "user_id": user["user_id"]}
    )
    if r.deleted_count == 0:
        raise HTTPException(404, "Episode not found.")
    return {"ok": True}


# ── Working Memory ────────────────────────────────────────────────

@router.get("/working")
async def get_working_memory(user=Depends(get_current_user)):
    """Return active session context for this user."""
    snippets = working_memory.get(user["user_id"], k=8)
    return {
        "snippets": snippets,
        "count": len(snippets),
        "stats": working_memory.stats(),
    }


# ── Statistics ────────────────────────────────────────────────────

@router.get("/stats")
async def memory_stats(user=Depends(get_current_user)):
    """Memory system statistics for the current user."""
    uid = user["user_id"]
    try:
        episode_count  = await mongo_db.episodes.count_documents({"user_id": uid})
        event_count    = await mongo_db.career_events.count_documents({"user_id": uid})
        activity_count = await mongo_db.activity_logs.count_documents({"user_id": uid})

        pipeline = [
            {"$match": {"user_id": uid}},
            {"$group": {"_id": "$episode_type", "count": {"$sum": 1},
                        "avg_importance": {"$avg": "$importance"}}},
        ]
        breakdown = await mongo_db.episodes.aggregate(pipeline).to_list(10)

        graph = await mongo_db.career_graph.find_one(
            {"user_id": uid}, {"_id": 0, "ai_notes": 1, "notes_updated_at": 1}
        ) or {}

        return {
            "episodes":         episode_count,
            "career_events":    event_count,
            "activity_logs":    activity_count,
            "episode_breakdown": breakdown,
            "ai_notes":         graph.get("ai_notes", ""),
            "notes_updated_at": graph.get("notes_updated_at", ""),
            "working_memory":   working_memory.get(uid, k=8),
        }
    except Exception as ex:
        logger.error("memory_stats failed user=%s: %s", uid, ex)
        raise HTTPException(500, "Failed to retrieve memory stats.")


# ── Manual Consolidation ──────────────────────────────────────────

@router.post("/consolidate")
async def trigger_consolidation(
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Trigger memory consolidation for this user (async)."""
    from memory_consolidation import consolidate_user_memory
    background_tasks.add_task(consolidate_user_memory, user["user_id"])
    return {"ok": True, "message": "Memory consolidation started in background."}
