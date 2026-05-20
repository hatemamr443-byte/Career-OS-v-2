"""Smart Onboarding — derives progress from real user state. No manual flags."""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from db import profiles, applications, users, onboarding as onboarding_col
from models import new_id
from auth import get_current_user

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

STEPS = [
    {
        "step_id":     "upload_cv",
        "title":       "Upload your CV",
        "description": "Parse your experience and skills automatically",
        "xp_reward":   30,
        "order":       1,
        "route":       "/profile",
    },
    {
        "step_id":     "complete_profile",
        "title":       "Complete your profile",
        "description": "Set target roles, location, and salary expectation",
        "xp_reward":   20,
        "order":       2,
        "route":       "/profile",
    },
    {
        "step_id":     "explore_jobs",
        "title":       "Explore jobs",
        "description": "Browse AI-recommended job matches for you",
        "xp_reward":   10,
        "order":       3,
        "route":       "/jobs",
    },
    {
        "step_id":     "apply_first_job",
        "title":       "Submit your first application",
        "description": "Apply to a job and track it in your pipeline",
        "xp_reward":   25,
        "order":       4,
        "route":       "/jobs",
    },
    {
        "step_id":     "enable_digest",
        "title":       "Enable daily digest",
        "description": "Get top job matches in your inbox every morning",
        "xp_reward":   15,
        "order":       5,
        "route":       "/profile",
    },
    {
        "step_id":     "reach_3day_streak",
        "title":       "3-day streak",
        "description": "Log in and take action 3 days in a row",
        "xp_reward":   40,
        "order":       6,
        "route":       "/dashboard",
    },
]


async def _derive_completed(user_id: str) -> set[str]:
    """Derive completed steps from live DB state — no stored flags needed."""
    profile   = await profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    user_doc  = await users.find_one({"user_id": user_id}, {"_id": 0}) or {}
    app_count = await applications.count_documents({"user_id": user_id})
    applied   = await applications.count_documents(
        {"user_id": user_id, "status": {"$ne": "discovered"}}
    )

    completed: set[str] = set()

    if profile.get("cv_text"):
        completed.add("upload_cv")

    profile_score = sum([
        bool(profile.get("skills") and len(profile.get("skills", [])) >= 3),
        bool(profile.get("target_roles")),
        bool(profile.get("headline")),
        bool(profile.get("years_experience")),
    ])
    if profile_score >= 3:
        completed.add("complete_profile")

    if app_count >= 1:
        completed.add("explore_jobs")

    if applied >= 1:
        completed.add("apply_first_job")

    if profile.get("daily_matches"):
        completed.add("enable_digest")

    if (user_doc.get("streak") or 0) >= 3:
        completed.add("reach_3day_streak")

    return completed


@router.get("")
async def get_onboarding(user=Depends(get_current_user)):
    """Return onboarding progress derived from real user state."""
    uid       = user["user_id"]
    completed = await _derive_completed(uid)
    steps     = [{**s, "completed": s["step_id"] in completed} for s in STEPS]
    done      = len(completed)
    xp_left   = sum(s["xp_reward"] for s in STEPS if s["step_id"] not in completed)

    return {
        "steps":           steps,
        "completed_count": done,
        "total_steps":     len(STEPS),
        "percent":         int(100 * done / len(STEPS)),
        "done":            done == len(STEPS),
        "total_xp_left":   xp_left,
    }
