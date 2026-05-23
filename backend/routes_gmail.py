"""Gmail OAuth integration — real read-only inbox access."""
import os
import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from db import profiles, emails as emails_col
from models import new_id
from auth import get_current_user
from llm_service import llm_call, parse_json_loose
from activity import log_activity
from xp import award_xp
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gmail", tags=["gmail"])

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE   = "https://gmail.googleapis.com/gmail/v1"
SCOPES           = (
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/userinfo.email"
)


def _creds() -> tuple[str, str, str]:
    cid      = os.environ.get("GOOGLE_CLIENT_ID", "")
    secret   = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect = os.environ.get("GOOGLE_REDIRECT_URI", "")
    if not all([cid, secret, redirect]):
        raise HTTPException(503, "Gmail OAuth is not configured on this deployment.")
    return cid, secret, redirect


@router.get("/connect")
async def gmail_connect(user=Depends(get_current_user)):
    """Return Google OAuth URL for user to authorize Gmail access."""
    cid, _, redirect = _creds()
    params = {
        "client_id":     cid,
        "redirect_uri":  redirect,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         user["user_id"],
    }
    return {"auth_url": GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)}


@router.get("/callback")
async def gmail_callback(code: str, state: str):
    """OAuth callback — exchange code for tokens, persist refresh token."""
    cid, secret, redirect = _creds()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     cid,
            "client_secret": secret,
            "redirect_uri":  redirect,
            "grant_type":    "authorization_code",
        })
    if resp.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {resp.text}")

    tokens = resp.json()
    now    = datetime.now(timezone.utc).isoformat()

    await profiles.update_one(
        {"user_id": state},
        {"$set": {
            "gmail_connected":    True,
            "gmail_refresh_token": tokens.get("refresh_token", ""),
            "gmail_connected_at": now,
        }},
        upsert=True,
    )

    # Award XP + log activity
    await award_xp(state, "gmail_connected")
    await log_activity(state, "gmail_connected", "Gmail connected",
                       "Gmail inbox integration activated", {})

    frontend = os.environ.get("DASHBOARD_URL", "")
    return RedirectResponse(f"{frontend}/emails?gmail=connected")


@router.get("/status")
async def gmail_status(user=Depends(get_current_user)):
    """Check if Gmail is connected."""
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    return {
        "connected":    bool(profile.get("gmail_connected")),
        "connected_at": profile.get("gmail_connected_at"),
    }


@router.post("/disconnect")
async def gmail_disconnect(user=Depends(get_current_user)):
    """Remove Gmail tokens and mark as disconnected."""
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$unset": {
            "gmail_refresh_token": "",
            "gmail_connected":     "",
            "gmail_connected_at":  "",
        }},
    )
    return {"ok": True}


async def _fresh_token(refresh_token: str) -> str | None:
    """Exchange refresh token for a fresh access token."""
    cid, secret, _ = _creds()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id":     cid,
            "client_secret": secret,
            "grant_type":    "refresh_token",
        })
    if r.status_code != 200:
        logger.error("Gmail token refresh failed: %s", r.text)
        return None
    return r.json().get("access_token")


async def _classify_email(from_addr: str, subject: str, snippet: str) -> dict:
    """Classify a single email. Uses llm_call directly (no user context available)."""
    try:
        text = await llm_call(
            task="fast",
            system=(
                "You are an AI classifying job-related emails. "
                "Return ONLY valid JSON — no prose, no markdown: "
                '{"classification":"interview|rejection|offer|recruiter_reachout|assessment|followup|ghosted|other",'
                '"confidence":0-100,"summary":"one sentence","urgency":"high|medium|low","next_steps":["action"]}'
            ),
            user=f"From: {from_addr}\nSubject: {subject}\nSnippet: {snippet}",
            session_id=f"cls_{hash(subject) % 999999}",
        )
        return parse_json_loose(text)
    except Exception as ex:
        logger.warning("email classification error: %s", ex)
        return {"classification": "other", "confidence": 0,
                "summary": "", "urgency": "low", "next_steps": []}


@router.post("/sync")
async def gmail_sync(
    user=Depends(get_current_user),
    max_messages: int = Query(30, ge=1, le=100),
):
    """Fetch latest Gmail messages, classify with AI, persist — idempotent."""
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    if not profile.get("gmail_connected") or not profile.get("gmail_refresh_token"):
        raise HTTPException(400, "Gmail not connected. Call /api/gmail/connect first.")

    access_token = await _fresh_token(profile["gmail_refresh_token"])
    if not access_token:
        raise HTTPException(401,
            "Could not refresh Gmail access token. Please reconnect your Gmail account.")

    headers = {"Authorization": f"Bearer {access_token}"}
    synced  = 0
    skipped = 0

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Fetch message list
        list_resp = await client.get(
            f"{GMAIL_API_BASE}/users/me/messages",
            headers=headers,
            params={"maxResults": max_messages, "q": "in:inbox"},
        )
        if list_resp.status_code != 200:
            raise HTTPException(502, f"Gmail list API error: {list_resp.status_code}")

        messages = list_resp.json().get("messages", [])

        for msg_ref in messages:
            gmail_id = msg_ref["id"]

            # Deduplication — skip already-synced messages
            if await emails_col.find_one(
                {"user_id": user["user_id"], "gmail_message_id": gmail_id}, {"_id": 1}
            ):
                skipped += 1
                continue

            # 2. Fetch message metadata
            detail = await client.get(
                f"{GMAIL_API_BASE}/users/me/messages/{gmail_id}",
                headers=headers,
                params={"format": "metadata",
                        "metadataHeaders": ["From", "Subject", "Date"]},
            )
            if detail.status_code != 200:
                continue

            msg      = detail.json()
            hdr_map  = {h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])}
            subject  = hdr_map.get("Subject", "(no subject)")
            from_raw = hdr_map.get("From", "")
            snippet  = msg.get("snippet", "")
            from_name = from_raw.split("<")[0].strip().strip('"')

            # 3. AI classification
            cls = await _classify_email(from_raw, subject, snippet)

            # 4. Persist
            await emails_col.insert_one({
                "email_id":         new_id("eml"),
                "user_id":          user["user_id"],
                "gmail_message_id": gmail_id,
                "thread_id":        msg.get("threadId", gmail_id),
                "from_addr":        from_raw,
                "from_name":        from_name,
                "subject":          subject,
                "body":             snippet,
                "classification":   cls.get("classification", "other"),
                "intent":           cls.get("summary", ""),
                "confidence":       cls.get("confidence", 0),
                "urgency":          cls.get("urgency", "low"),
                "next_steps":       cls.get("next_steps", []),
                "is_read":          False,
                "received_at":      datetime.now(timezone.utc).isoformat(),
            })
            synced += 1

    # Log sync activity
    if synced > 0:
        await log_activity(
            user["user_id"], "inbox_sync",
            f"Inbox synced — {synced} new emails",
            f"Gmail sync processed {synced} new messages, {skipped} already seen.",
            {"synced": synced, "skipped": skipped},
        )

    return {"synced": synced, "skipped": skipped, "total": synced + skipped}
