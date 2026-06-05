"""Gamification: missions, XP, streak, AI coach."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from db import users, missions, applications, profiles, coach_messages
from models import new_id, CoachChatRequest
from auth import get_current_user
from llm_service import parse_json_loose
from orchestrator import orchestrator

router = APIRouter(prefix="/api", tags=["gamification"])


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _level_for_xp(xp: int) -> int:
    # Level curve: 100, 250, 450, 700, 1000, ...
    thresholds = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000]
    lvl = 1
    for i, t in enumerate(thresholds):
        if xp >= t:
            lvl = i + 1
    return lvl


def _xp_progress(xp: int):
    thresholds = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000]
    for i in range(len(thresholds) - 1):
        if thresholds[i] <= xp < thresholds[i + 1]:
            current = xp - thresholds[i]
            needed = thresholds[i + 1] - thresholds[i]
            return {"current": current, "needed": needed, "percent": int(100 * current / needed)}
    return {"current": 0, "needed": 1000, "percent": 100}


@router.get("/missions/today")
async def get_today_missions(user=Depends(get_current_user)):
    today = _today()
    docs = await missions.find(
        {"user_id": user["user_id"], "date": today}, {"_id": 0}
    ).to_list(20)
    if docs:
        return {"missions": docs, "date": today}

    # Generate via AI based on user state
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    apps = await applications.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    pending = [a for a in apps if a["status"] in ("under_review", "interview")]
    discovered = [a for a in apps if a["status"] == "discovered"]

    system = (
        "You are an AI Career Coach generating today's 4 missions for a job seeker. "
        "Missions must reinforce GOOD decisions, not random tasks. Return ONLY JSON: "
        '{"missions": [{"title": "...", "description": "...", "action_type": "apply|review|update_cv|reflect|research", "xp_reward": 10-30, "reasoning": "why this mission for this user today"}]}'
    )
    context = (
        f"User: {profile.get('headline', 'Job seeker') if profile else 'New user'}\n"
        f"Skills: {', '.join((profile or {}).get('skills', [])[:8])}\n"
        f"Total applications: {len(apps)}\n"
        f"Pending interviews/reviews: {len(pending)}\n"
        f"Discovered (not applied): {len(discovered)}\n"
        f"Streak: {user.get('streak', 0)} days\n"
        f"XP: {user.get('xp', 0)}\n\n"
        "Generate 4 missions tailored to this state. If user is new, focus on profile completion + first application."
    )
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="daily_missions",
            task="reasoning",
            feature_prompt=system,
            user_message=context,
            session_id=f"missions_{user['user_id']}_{today}",
        )
        data = parse_json_loose(text)
        ms = data.get("missions", [])
        if not ms:
            raise ValueError("empty")
    except Exception:
        ms = [
            {
                "title": "Apply to 1 high-match job",
                "description": "Pick a job with 70%+ match score and submit your application.",
                "action_type": "apply",
                "xp_reward": 25,
                "reasoning": "Daily action toward goal."
            },
            {
                "title": "Review your top 3 recommendations",
                "description": "Open the Jobs tab and read the AI reasoning for your top picks.",
                "action_type": "review",
                "xp_reward": 10,
                "reasoning": "Smart job hunting."
            },
            {
                "title": "Reflect on rejections",
                "description": "Check your insights — any pattern? Note one improvement.",
                "action_type": "reflect",
                "xp_reward": 15,
                "reasoning": "Learning loop."
            },
            {
                "title": "Polish your CV headline",
                "description": "Open Profile → make your headline sharper and more specific.",
                "action_type": "update_cv",
                "xp_reward": 15,
                "reasoning": "Strong first impression."
            },
        ]

    docs = []
    for m in ms[:5]:
        docs.append({
            "mission_id": new_id("mis"),
            "user_id": user["user_id"],
            "date": today,
            "title": m.get("title", "Mission"),
            "description": m.get("description", ""),
            "action_type": m.get("action_type", "review"),
            "target_id": None,
            "xp_reward": int(m.get("xp_reward", 10)),
            "completed": False,
            "completed_at": None,
            "reasoning": m.get("reasoning", ""),
        })
    if docs:
        await missions.insert_many(docs)
        for d in docs:
            d.pop("_id", None)
    return {"missions": docs, "date": today}


@router.post("/missions/{mission_id}/complete")
async def complete_mission(mission_id: str, user=Depends(get_current_user)):
    m = await missions.find_one(
        {"mission_id": mission_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not m:
        raise HTTPException(404, "Mission not found")
    if m.get("completed"):
        return {"ok": True, "already": True}

    now = datetime.now(timezone.utc)
    await missions.update_one(
        {"mission_id": mission_id},
        {"$set": {"completed": True, "completed_at": now.isoformat()}},
    )

    # Award XP, update streak
    today = _today()
    last_active = user.get("last_active_date")
    new_streak = user.get("streak", 0)
    if last_active != today:
        if last_active:
            yday = (now.date() - timedelta(days=1)).isoformat()
            new_streak = (user.get("streak", 0) + 1) if last_active == yday else 1
        else:
            new_streak = 1
    new_xp = (user.get("xp", 0) or 0) + int(m["xp_reward"])
    new_level = _level_for_xp(new_xp)

    await users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "xp": new_xp,
            "level": new_level,
            "streak": new_streak,
            "last_active_date": today,
        }},
    )
    return {"ok": True, "xp_gained": m["xp_reward"], "xp": new_xp, "level": new_level, "streak": new_streak}


@router.get("/me/stats")
async def my_stats(user=Depends(get_current_user)):
    fresh = await users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    progress = _xp_progress(fresh.get("xp", 0) or 0)
    return {
        "xp": fresh.get("xp", 0) or 0,
        "level": fresh.get("level", 1) or 1,
        "streak": fresh.get("streak", 0) or 0,
        "progress": progress,
    }


@router.get("/coach/messages")
async def coach_history(user=Depends(get_current_user)):
    docs = await coach_messages.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    return {"messages": docs}


@router.post("/coach/chat")
async def coach_chat(payload: CoachChatRequest, user=Depends(get_current_user)):
    content = (payload.message or "").strip()
    if not content:
        raise HTTPException(400, "message required")

    now = datetime.now(timezone.utc)
    await coach_messages.insert_one({
        "message_id": new_id("msg"),
        "user_id": user["user_id"],
        "role": "user",
        "content": content,
        "created_at": now.isoformat(),
    })

    apps = await applications.count_documents({"user_id": user["user_id"]})
    interviews = await applications.count_documents({"user_id": user["user_id"], "status": "interview"})

    try:
        reply = await orchestrator.run(
            user_id=user["user_id"],
            feature="coach_chat",
            task="reasoning",
            feature_prompt=(
                "You are an elite, no-fluff AI Career Coach with full knowledge "
                "of this user's career history. Be direct, actionable, and warm. "
                "Keep responses under 150 words. Suggest concrete next steps. "
                "Never use emojis. Never use generic motivational fluff."
            ),
            user_message=(
                f"Applications: {apps}, Interviews: {interviews}\n"
                f"Streak: {user.get('streak', 0)} days, Level: {user.get('level', 1)}\n\n"
                f"User asks: {content}"
            ),
            session_id=f"coach_{user['user_id']}",
            context_depth="full",
        )
    except Exception as ex:
        reply = f"Coach is offline right now. Try again in a moment. ({type(ex).__name__})"

    await coach_messages.insert_one({
        "message_id": new_id("msg"),
        "user_id": user["user_id"],
        "role": "assistant",
        "content": reply,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"reply": reply}


# ─────────────────────────────────────────────
# INTERNAL XP HELPER (called from other routes)
# ─────────────────────────────────────────────

async def _award_xp_direct(user_id: str, amount: int, reason: str):
    """Award XP directly to a user from any route. Delegates to the xp engine."""
    from xp import award_xp
    return await award_xp(user_id, reason, amount=amount)


@router.get("/xp/history")
async def xp_history(user=Depends(get_current_user), limit: int = 20):
    """Return recent XP events for the current user."""
    from db import xp_events
    docs = await xp_events.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"events": docs, "count": len(docs)}
