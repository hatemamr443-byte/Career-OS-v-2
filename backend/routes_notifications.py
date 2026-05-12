"""Notifications: daily digest toggle + manual trigger + cron endpoint."""
import os
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from datetime import datetime, timezone
from db import profiles
from auth import get_current_user
from daily_digest import run_daily_digest_for_user, run_daily_digest_all
from emailer import _configured as email_configured

router = APIRouter(prefix="/api", tags=["notifications"])


@router.put("/profile/notifications")
async def update_notifications(payload: dict, user=Depends(get_current_user)):
    """Toggle daily_matches on/off for the current user."""
    enabled = bool(payload.get("daily_matches"))
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"daily_matches": enabled}, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    return {
        "daily_matches": enabled,
        "email_configured": email_configured(),
        "email_target": user["email"],
    }


@router.post("/profile/notifications/test")
async def send_test_digest(http_request: Request, user=Depends(get_current_user)):
    """Run the daily digest right now for the calling user (manual test)."""
    origin = str(http_request.base_url).rstrip("/")
    result = await run_daily_digest_for_user(user, dashboard_url=origin)
    return result


@router.post("/internal/run-daily-digest")
async def cron_run_daily_digest(
    http_request: Request,
    x_cron_token: str = Header(default=""),
):
    """Cron endpoint — hit this from cron-job.org daily.
    Requires X-Cron-Token header matching CRON_TOKEN env var (set this in production).
    """
    expected = os.environ.get("CRON_TOKEN", "")
    if not expected:
        raise HTTPException(503, "CRON_TOKEN not configured on the server.")
    if x_cron_token != expected:
        raise HTTPException(401, "Invalid cron token.")
    origin = str(http_request.base_url).rstrip("/")
    return await run_daily_digest_all(dashboard_url=origin)
