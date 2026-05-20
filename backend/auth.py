"""Auth abstraction layer - currently Emergent Google OAuth, designed to support JWT later.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

from db import users, sessions
from models import User, new_id, now_utc

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


# ---------- Auth Service Abstraction ----------
class AuthService:
    """Abstract auth provider so we can plug in JWT later without refactoring callers."""

    async def authenticate_request(self, request: Request) -> Optional[dict]:
        token = request.cookies.get("session_token")
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
        if not token:
            return None

        sess = await sessions.find_one({"session_token": token}, {"_id": 0})
        if not sess:
            return None

        expires_at = sess.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at < datetime.now(timezone.utc):
            return None

        user_doc = await users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
        return user_doc


auth_service = AuthService()


async def get_current_user(request: Request) -> dict:
    user = await auth_service.authenticate_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ---------- Routes ----------
@router.post("/session")
async def create_session(payload: dict, response: Response):
    """Exchange Emergent session_id for a session_token cookie."""
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(EMERGENT_AUTH_URL, headers={"X-Session-ID": session_id})
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        data = r.json()

    email = data["email"]
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data["session_token"]

    # Upsert user
    existing = await users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = new_id("user")
        user = User(user_id=user_id, email=email, name=name, picture=picture)
        doc = user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await users.insert_one(doc)
        # Fire-and-forget welcome email
        try:
            from welcome_emails import send_welcome_sequence_day0
            import asyncio
            asyncio.create_task(send_welcome_sequence_day0(user_id, email, name))
        except Exception:
            pass

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": user_id,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60,
    )

    user_doc = await users.find_one({"user_id": user_id}, {"_id": 0})
    if user_doc and isinstance(user_doc.get("created_at"), str):
        pass
    return {"user": user_doc, "session_token": session_token}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}
