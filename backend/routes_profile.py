"""Profile / CV / identity graph."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import profiles
from auth import get_current_user
from llm_service import llm_call, parse_json_loose

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile(user=Depends(get_current_user)):
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p or {}


@router.put("")
async def update_profile(payload: dict, user=Depends(get_current_user)):
    payload.pop("user_id", None)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": payload, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p


@router.post("/parse-cv")
async def parse_cv(payload: dict, user=Depends(get_current_user)):
    cv_text = (payload.get("cv_text") or "").strip()
    if not cv_text:
        raise HTTPException(400, "cv_text required")

    system = (
        "You are an expert CV parser. Extract structured profile data. "
        "Return ONLY JSON: "
        '{"headline": "1-line professional headline", '
        '"skills": ["lowercase skills"], '
        '"target_roles": ["3-5 likely target roles"], '
        '"years_experience": int}'
    )
    try:
        text = await llm_call(
            task="reasoning",
            system=system,
            user=cv_text,
            session_id=f"cv_{user['user_id']}",
        )
        data = parse_json_loose(text)
    except Exception:
        data = {}

    update = {
        "cv_text": cv_text,
        "headline": data.get("headline", "Professional"),
        "skills": [s.lower() for s in (data.get("skills") or [])][:30],
        "target_roles": (data.get("target_roles") or [])[:5],
        "years_experience": data.get("years_experience"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": update, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p
