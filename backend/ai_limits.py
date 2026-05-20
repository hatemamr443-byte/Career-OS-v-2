"""
AI Rate Limiter + Quota Gating.
Protects all LLM endpoints from abuse and enforces plan limits.

Usage:
    from ai_limits import check_ai_quota, AI_LIMITS

    @router.post("/cv/tailor")
    async def tailor_cv(payload: dict, user=Depends(get_current_user)):
        await check_ai_quota(user, "cv_tailor")
        ...
"""
from datetime import datetime, timezone
from fastapi import HTTPException
from db import db as mongo_db
from quota import get_effective_plan
import logging

logger = logging.getLogger(__name__)

ai_usage = mongo_db.ai_usage   # collection: {user_id, feature, date, count}

# ── Per-day limits per plan ───────────────────────────────────────
AI_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        "cv_tailor":        2,
        "ats_score":        3,
        "cover_letter":     2,
        "interview_questions": 3,
        "interview_evaluate":  10,
        "company_research":    3,
        "salary_range":        3,
        "evaluate_offer":      2,
        "negotiate":           2,
        "cost_of_living":      2,
        "ai_match":            5,   # existing match limit (per month, handled separately)
    },
    "pro": {
        "cv_tailor":        20,
        "ats_score":        50,
        "cover_letter":     20,
        "interview_questions": 30,
        "interview_evaluate":  100,
        "company_research":    20,
        "salary_range":        20,
        "evaluate_offer":      20,
        "negotiate":           20,
        "cost_of_living":      20,
        "ai_match":            999,
    },
    "team": {
        # Team = unlimited on all features
        "__default__": 9999,
    },
}

UPGRADE_MESSAGE = (
    "Daily AI limit reached for your plan. "
    "Upgrade to Pro for 10x more AI actions. "
    "Visit /billing to upgrade."
)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def get_ai_usage(user_id: str, feature: str, date: str | None = None) -> int:
    """Return how many times a user used a feature today."""
    day = date or _today()
    doc = await ai_usage.find_one(
        {"user_id": user_id, "feature": feature, "date": day},
        {"_id": 0, "count": 1},
    )
    return doc["count"] if doc else 0


async def increment_ai_usage(user_id: str, feature: str) -> int:
    """Increment usage counter. Returns new count."""
    day = _today()
    result = await ai_usage.find_one_and_update(
        {"user_id": user_id, "feature": feature, "date": day},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True,
    )
    return result.get("count", 1) if result else 1


def _get_limit(plan: str, feature: str) -> int:
    plan_limits = AI_LIMITS.get(plan, AI_LIMITS["free"])
    if "__default__" in plan_limits:
        return plan_limits["__default__"]
    return plan_limits.get(feature, 5)


async def check_ai_quota(user: dict, feature: str) -> None:
    """
    Raises HTTP 429 if user exceeded their daily AI quota for this feature.
    Call this at the START of every AI endpoint before doing any LLM work.
    """
    user_id = user.get("user_id", "")
    plan    = await get_effective_plan(user)

    # Trial users get Pro limits
    if user.get("trial_active"):
        plan = "pro"

    limit   = _get_limit(plan, feature)
    current = await get_ai_usage(user_id, feature)

    if current >= limit:
        logger.warning(
            "AI quota exceeded: user=%s feature=%s plan=%s usage=%d/%d",
            user_id, feature, plan, current, limit,
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error":   "quota_exceeded",
                "feature": feature,
                "plan":    plan,
                "used":    current,
                "limit":   limit,
                "message": UPGRADE_MESSAGE,
                "upgrade_url": "/billing",
            },
        )

    # Increment AFTER the check (before the actual LLM call)
    await increment_ai_usage(user_id, feature)


async def get_ai_usage_summary(user_id: str, plan: str) -> dict:
    """Return today's usage summary for all features."""
    day = _today()
    docs = await ai_usage.find(
        {"user_id": user_id, "date": day},
        {"_id": 0, "feature": 1, "count": 1},
    ).to_list(50)

    usage_map = {d["feature"]: d["count"] for d in docs}
    plan_limits = AI_LIMITS.get(plan, AI_LIMITS["free"])

    summary = {}
    for feature, limit in plan_limits.items():
        if feature == "__default__":
            continue
        used = usage_map.get(feature, 0)
        summary[feature] = {
            "used":      used,
            "limit":     limit,
            "remaining": max(0, limit - used),
            "exhausted": used >= limit,
        }
    return summary
