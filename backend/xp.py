"""XP Engine — persistent gamification layer. Render-safe."""
from datetime import datetime, timezone, timedelta
from db import users, xp_events
from models import new_id
from notifications import push_notification
import logging

logger = logging.getLogger(__name__)

XP_RULES: dict[str, int] = {
    "job_applied":          25,
    "status_under_review":  10,
    "status_interview":     75,
    "status_offer":        150,
    "cv_uploaded":          30,
    "profile_updated":      20,
    "onboarding_complete": 100,
    "gmail_connected":      50,
    "streak_milestone_3":   40,
    "streak_milestone_7":   80,
    "job_saved":            10,
}

# XP required to reach each level (index = level - 1)
LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000]


def level_for_xp(xp: int) -> int:
    lvl = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            lvl = i + 1
    return min(lvl, len(LEVEL_THRESHOLDS))


def xp_progress(xp: int) -> dict:
    """Return current/needed XP for progress bar within current level."""
    for i in range(len(LEVEL_THRESHOLDS) - 1):
        lo, hi = LEVEL_THRESHOLDS[i], LEVEL_THRESHOLDS[i + 1]
        if lo <= xp < hi:
            current = xp - lo
            needed  = hi - lo
            return {"current": current, "needed": needed,
                    "percent": int(100 * current / needed)}
    # Max level
    return {"current": XP_RULES.get("job_applied", 25),
            "needed":  XP_RULES.get("job_applied", 25),
            "percent": 100}


async def award_xp(user_id: str, reason: str, amount: int | None = None) -> dict:
    """
    Award XP, update level + streak, push level-up notification if needed.
    Returns result dict. Never raises.
    """
    try:
        xp_amount = amount if amount is not None else XP_RULES.get(reason, 10)
        user_doc  = await users.find_one({"user_id": user_id}) or {}
        old_xp    = user_doc.get("xp") or 0
        old_level = user_doc.get("level") or 1

        new_xp    = old_xp + xp_amount
        new_level = level_for_xp(new_xp)
        level_up  = new_level > old_level

        # ── Streak ──────────────────────────────────────────
        now         = datetime.now(timezone.utc)
        today       = now.date().isoformat()
        last_active = user_doc.get("last_active_date")
        streak      = user_doc.get("streak") or 0

        if last_active and last_active != today:
            yesterday = (now.date() - timedelta(days=1)).isoformat()
            streak    = (streak + 1) if last_active == yesterday else 1
        elif not last_active:
            streak = 1
        # else: already active today — don't change streak

        longest = max(user_doc.get("longest_streak") or 0, streak)

        await users.update_one(
            {"user_id": user_id},
            {"$set": {
                "xp": new_xp, "level": new_level,
                "streak": streak, "longest_streak": longest,
                "last_active_date": today,
            }},
        )

        # ── Persist XP event ────────────────────────────────
        await xp_events.insert_one({
            "event_id":  new_id("xpe"),
            "user_id":   user_id,
            "reason":    reason,
            "amount":    xp_amount,
            "new_total": new_xp,
            "new_level": new_level,
            "level_up":  level_up,
            "created_at": now.isoformat(),
        })

        # ── Level-up notification ────────────────────────────
        if level_up:
            await push_notification(
                user_id, "level_up",
                f"Level Up! You're now Level {new_level} 🎉",
                f"Earned {xp_amount} XP and reached Level {new_level}. Keep going!",
                {"new_level": new_level, "new_xp": new_xp},
            )

        # ── Streak milestones ────────────────────────────────
        if streak in (3, 7, 14, 30) and last_active != today:
            await push_notification(
                user_id, "streak_reward",
                f"{streak}-Day Streak! 🔥",
                f"You've been active {streak} days in a row. Keep it up!",
                {"streak": streak},
            )

        return {
            "xp_awarded": xp_amount,
            "reason":     reason,
            "new_xp":     new_xp,
            "new_level":  new_level,
            "level_up":   level_up,
            "streak":     streak,
            "progress":   xp_progress(new_xp),
        }

    except Exception as ex:
        logger.warning("award_xp failed (user=%s reason=%s): %s", user_id, reason, ex)
        return {"xp_awarded": 0, "reason": reason, "error": str(ex)}
