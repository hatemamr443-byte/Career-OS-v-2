"""Plan-based quota / usage tracking."""
from datetime import datetime, timezone
from db import db as mongo_db, users as users_col

match_usage = mongo_db.match_usage

FREE_MATCH_LIMIT = 5


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def get_effective_plan(user: dict) -> str:
    """Returns 'free' | 'pro' | 'team', accounting for expired paid plans."""
    plan = user.get("plan") or "free"
    if plan == "free":
        return "free"
    expires = user.get("plan_expires_at")
    if not expires:
        return "free"
    if isinstance(expires, str):
        try:
            exp = datetime.fromisoformat(expires)
        except Exception:
            return "free"
    else:
        exp = expires
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        # Auto-downgrade
        await users_col.update_one(
            {"user_id": user["user_id"]}, {"$set": {"plan": "free"}}
        )
        return "free"
    return plan


async def get_match_usage(user_id: str) -> int:
    doc = await match_usage.find_one(
        {"user_id": user_id, "month": _current_month()}, {"_id": 0}
    )
    return (doc or {}).get("count", 0)


async def increment_match_usage(user_id: str) -> int:
    month = _current_month()
    res = await match_usage.find_one_and_update(
        {"user_id": user_id, "month": month},
        {"$inc": {"count": 1}, "$setOnInsert": {"user_id": user_id, "month": month}},
        upsert=True,
        return_document=True,
        projection={"_id": 0},
    )
    return (res or {}).get("count", 1)


async def usage_summary(user: dict) -> dict:
    plan = await get_effective_plan(user)
    used = await get_match_usage(user["user_id"])
    if plan in ("pro", "team"):
        return {
            "plan": plan,
            "matches_used": used,
            "matches_limit": None,  # unlimited
            "remaining": None,
            "over_limit": False,
            "near_limit": False,
        }
    remaining = max(0, FREE_MATCH_LIMIT - used)
    return {
        "plan": plan,
        "matches_used": used,
        "matches_limit": FREE_MATCH_LIMIT,
        "remaining": remaining,
        "over_limit": used >= FREE_MATCH_LIMIT,
        "near_limit": used >= FREE_MATCH_LIMIT - 1,
    }
