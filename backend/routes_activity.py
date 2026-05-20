"""Activity Feed, Profile Completeness, Onboarding — P1 Retention Core."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import (
    activity_logs, profiles, applications, users,
    onboarding as onboarding_col, xp_events, notifications as notif_col
)
from models import new_id
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["activity"])


# ─────────────────────────────────────────────
# ACTIVITY FEED
# ─────────────────────────────────────────────

async def log_activity(
    user_id: str,
    event_type: str,
    title: str,
    description: str,
    metadata: dict | None = None,
):
    """Write one activity event. Fire-and-forget from other routes."""
    doc = {
        "activity_id": new_id("act"),
        "user_id": user_id,
        "event_type": event_type,
        "title": title,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await activity_logs.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/insights/activity")
async def get_activity(
    user=Depends(get_current_user),
    limit: int = 15,
):
    """User activity timeline — real events only, no mock data."""
    docs = await activity_logs.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"events": docs, "count": len(docs)}


# ─────────────────────────────────────────────
# PROFILE COMPLETENESS ENGINE
# ─────────────────────────────────────────────

def _score_profile(profile: dict) -> dict:
    """Weighted completeness scoring. Returns percent + missing + suggestions."""
    weights = {
        "cv_text":          {"weight": 30, "label": "Upload or paste your CV"},
        "skills":           {"weight": 20, "label": "Add at least 3 skills"},
        "target_roles":     {"weight": 15, "label": "Set target roles"},
        "headline":         {"weight": 15, "label": "Write a professional headline"},
        "years_experience": {"weight": 10, "label": "Set years of experience"},
        "target_locations": {"weight": 5,  "label": "Add preferred locations"},
        "salary_min":       {"weight": 5,  "label": "Set a salary expectation"},
    }
    total_weight = sum(v["weight"] for v in weights.values())
    earned = 0
    missing_fields = []
    suggestions = []

    for field, cfg in weights.items():
        val = profile.get(field)
        filled = False
        if field == "skills":
            filled = isinstance(val, list) and len(val) >= 3
        elif field == "target_roles":
            filled = isinstance(val, list) and len(val) >= 1
        elif field == "target_locations":
            filled = isinstance(val, list) and len(val) >= 1
        else:
            filled = bool(val)

        if filled:
            earned += cfg["weight"]
        else:
            missing_fields.append(field)
            suggestions.append(cfg["label"])

    percent = int(100 * earned / total_weight)
    status = "complete" if percent >= 80 else ("in_progress" if percent >= 40 else "empty")

    return {
        "percent": percent,
        "missing_fields": missing_fields,
        "suggestions": suggestions,
        "status": status,
    }


@router.get("/profile/completeness")
async def profile_completeness(user=Depends(get_current_user)):
    """Return weighted profile completeness score + actionable suggestions."""
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile:
        return {
            "percent": 0,
            "missing_fields": ["cv_text", "skills", "target_roles", "headline", "years_experience"],
            "suggestions": [
                "Upload or paste your CV",
                "Add at least 3 skills",
                "Set target roles",
                "Write a professional headline",
                "Set years of experience",
            ],
            "status": "empty",
        }
    return _score_profile(profile)


# ─────────────────────────────────────────────
# SMART ONBOARDING SYSTEM
# ─────────────────────────────────────────────

ONBOARDING_STEPS = [
    {"step_id": "upload_cv",        "title": "Upload your CV",       "description": "Parse your experience and skills automatically", "xp_reward": 30, "order": 1},
    {"step_id": "complete_profile", "title": "Complete your profile","description": "Set target roles, location, salary expectation", "xp_reward": 20, "order": 2},
    {"step_id": "save_first_job",   "title": "Save your first job",  "description": "Browse Jobs and save one that interests you",    "xp_reward": 10, "order": 3},
    {"step_id": "apply_first_job",  "title": "Apply to a job",       "description": "Submit your first application via Career OS",    "xp_reward": 25, "order": 4},
    {"step_id": "enable_digest",    "title": "Enable daily digest",  "description": "Get top matches emailed to you every morning",   "xp_reward": 15, "order": 5},
    {"step_id": "reach_3day_streak","title": "Reach a 3-day streak", "description": "Log in and complete missions for 3 days in a row","xp_reward": 40, "order": 6},
]


@router.get("/onboarding")
async def get_onboarding(user=Depends(get_current_user)):
    """Return onboarding progress with real state checks."""
    uid = user["user_id"]

    # Fetch real state
    profile      = await profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    app_count    = await applications.count_documents({"user_id": uid})
    user_doc     = await users.find_one({"user_id": uid}, {"_id": 0}) or {}
    digest_on    = profile.get("daily_matches", False)
    streak       = user_doc.get("streak", 0)

    # Derive completed steps from real data
    completed_ids = set()
    if profile.get("cv_text"):
        completed_ids.add("upload_cv")

    completeness = _score_profile(profile)
    if completeness["percent"] >= 60:
        completed_ids.add("complete_profile")

    if app_count >= 1:
        completed_ids.add("save_first_job")

    applied = await applications.count_documents({"user_id": uid, "status": {"$ne": "discovered"}})
    if applied >= 1:
        completed_ids.add("apply_first_job")

    if digest_on:
        completed_ids.add("enable_digest")

    if streak >= 3:
        completed_ids.add("reach_3day_streak")

    # Load any persisted overrides
    stored = await onboarding_col.find_one({"user_id": uid}, {"_id": 0}) or {}
    persisted_completed = set(stored.get("completed_ids", []))
    completed_ids = completed_ids | persisted_completed

    steps = []
    for s in ONBOARDING_STEPS:
        steps.append({
            **s,
            "completed": s["step_id"] in completed_ids,
        })

    completed_count = sum(1 for s in steps if s["completed"])
    total_xp_available = sum(s["xp_reward"] for s in steps if not s["completed"])
    percent = int(100 * completed_count / len(steps))

    return {
        "steps": steps,
        "completed_count": completed_count,
        "total_steps": len(steps),
        "percent": percent,
        "done": completed_count == len(steps),
        "total_xp_available": total_xp_available,
    }


@router.post("/onboarding/{step_id}/complete")
async def complete_onboarding_step(step_id: str, user=Depends(get_current_user)):
    """Mark a step manually complete (for non-auto-derivable steps)."""
    valid_ids = {s["step_id"] for s in ONBOARDING_STEPS}
    if step_id not in valid_ids:
        raise HTTPException(400, "Invalid step_id")

    uid = user["user_id"]
    stored = await onboarding_col.find_one({"user_id": uid}) or {}
    completed = set(stored.get("completed_ids", []))
    already = step_id in completed
    completed.add(step_id)

    await onboarding_col.update_one(
        {"user_id": uid},
        {"$set": {"completed_ids": list(completed), "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    # Log activity
    if not already:
        step_info = next(s for s in ONBOARDING_STEPS if s["step_id"] == step_id)
        await log_activity(uid, "onboarding_step", step_info["title"],
                           f"Completed onboarding: {step_info['title']}", {"step_id": step_id})

    return {"ok": True, "step_id": step_id, "already": already}


# ─────────────────────────────────────────────
# IN-APP NOTIFICATIONS
# ─────────────────────────────────────────────

async def push_notification(
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    metadata: dict | None = None,
):
    """Create a notification for a user. Called internally from other routes."""
    doc = {
        "notification_id": new_id("ntf"),
        "user_id": user_id,
        "type": notif_type,
        "title": title,
        "message": message,
        "metadata": metadata or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await notif_col.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/notifications")
async def list_notifications(
    user=Depends(get_current_user),
    limit: int = 20,
    unread_only: bool = False,
):
    """List in-app notifications for the current user."""
    query: dict = {"user_id": user["user_id"]}
    if unread_only:
        query["read"] = False

    docs = await notif_col.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    unread_count = await notif_col.count_documents({"user_id": user["user_id"], "read": False})
    return {"notifications": docs, "unread_count": unread_count}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user=Depends(get_current_user)):
    res = await notif_col.update_one(
        {"notification_id": notification_id, "user_id": user["user_id"]},
        {"$set": {"read": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.patch("/notifications/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await notif_col.update_many(
        {"user_id": user["user_id"], "read": False},
        {"$set": {"read": True}},
    )
    return {"ok": True}


@router.get("/notifications/unread-count")
async def unread_count(user=Depends(get_current_user)):
    count = await notif_col.count_documents({"user_id": user["user_id"], "read": False})
    return {"unread_count": count}
