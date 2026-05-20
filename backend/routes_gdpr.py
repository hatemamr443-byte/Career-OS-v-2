"""
GDPR Compliance Routes.
EU users have the right to: access, export, and delete their data.

Endpoints:
  GET  /api/me/export-data   → full data export (JSON)
  DELETE /api/me/account     → permanent account deletion
  GET  /api/me/data-summary  → what data we hold
"""
import os
import json
import zipfile
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from db import (
    users, profiles, jobs, applications, activity_logs,
    notifications, xp_events, cv_versions, interview_sessions,
    emails as emails_col, referrals, bookmarks, ai_usage,
    db as mongo_db,
)
from auth import get_current_user
from models import new_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/me", tags=["gdpr"])


# ─────────────────────────────────────────────
# DATA SUMMARY (what we hold)
# ─────────────────────────────────────────────

@router.get("/data-summary")
async def data_summary(user=Depends(get_current_user)):
    """Return a summary of what data Career OS holds about this user."""
    uid = user["user_id"]
    counts = {}
    for name, col in [
        ("applications",    applications),
        ("activity_events", activity_logs),
        ("notifications",   notifications),
        ("cv_versions",     cv_versions),
        ("interview_sessions", interview_sessions),
        ("xp_events",       xp_events),
        ("emails_synced",   emails_col),
        ("bookmarks",       bookmarks),
        ("ai_usage_records", ai_usage),
    ]:
        counts[name] = await col.count_documents({"user_id": uid})

    user_doc  = await users.find_one({"user_id": uid}, {"_id": 0}) or {}
    prof_doc  = await profiles.find_one({"user_id": uid}, {"_id": 0}) or {}

    return {
        "user_id":     uid,
        "email":       user_doc.get("email"),
        "member_since": user_doc.get("created_at"),
        "data_held":   counts,
        "profile_complete": bool(prof_doc.get("cv_text")),
        "gmail_connected": bool(prof_doc.get("gmail_connected")),
        "gdpr_rights": {
            "export": "GET /api/me/export-data",
            "delete": "DELETE /api/me/account",
            "contact": "privacy@career-os.io",
        },
    }


# ─────────────────────────────────────────────
# DATA EXPORT (Right to Portability)
# ─────────────────────────────────────────────

@router.get("/export-data")
async def export_data(user=Depends(get_current_user)):
    """
    Export all user data as a downloadable ZIP archive (GDPR Article 20).
    Contains: profile, applications, CV versions, activity, emails.
    """
    uid = user["user_id"]
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    async def _fetch(col, query=None) -> list:
        q = query or {"user_id": uid}
        return await col.find(q, {"_id": 0}).to_list(10_000)

    # Collect all data
    data = {
        "user":               await users.find_one({"user_id": uid}, {"_id": 0, "google_token": 0}) or {},
        "profile":            await profiles.find_one({"user_id": uid}, {"_id": 0, "gmail_refresh_token": 0}) or {},
        "applications":       await _fetch(applications),
        "cv_versions":        await _fetch(cv_versions),
        "interview_sessions": await _fetch(interview_sessions),
        "activity_feed":      await _fetch(activity_logs),
        "notifications":      await _fetch(notifications),
        "bookmarks":          await _fetch(bookmarks),
        "xp_events":          await _fetch(xp_events),
        "emails_metadata":    await _fetch(emails_col),  # metadata only, no body content
        "referral_info":      await referrals.find_one({"referrer_id": uid}, {"_id": 0}) or {},
        "export_info": {
            "exported_at": now,
            "user_id":     uid,
            "note":        "This export contains all personal data Career OS holds. Sensitive tokens (OAuth refresh tokens) are excluded.",
        },
    }

    # Build ZIP in memory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for section, content in data.items():
            zf.writestr(
                f"{section}.json",
                json.dumps(content, indent=2, default=str),
            )
        # Add human-readable summary
        zf.writestr("README.txt", f"""Career OS — Data Export
Generated: {now}
User: {data['user'].get('email', uid)}

This archive contains all personal data Career OS holds about you.
Files:
- user.json           Your account information
- profile.json        Career profile, CV text, skills
- applications.json   All job applications and status history
- cv_versions.json    Saved tailored CV versions
- interview_sessions.json  Interview prep sessions
- activity_feed.json  Timeline of all actions
- emails_metadata.json     Synced email metadata (no body content)
- bookmarks.json      Saved jobs
- xp_events.json      Gamification history

To request account deletion: DELETE /api/me/account
Questions: privacy@career-os.io
""")

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="career-os-export-{now}.zip"',
        },
    )


# ─────────────────────────────────────────────
# ACCOUNT DELETION (Right to Erasure)
# ─────────────────────────────────────────────

@router.delete("/account")
async def delete_account(
    user=Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Permanently delete all user data (GDPR Article 17 — Right to Erasure).
    This action is IRREVERSIBLE.
    """
    uid = user["user_id"]
    logger.warning("GDPR ACCOUNT DELETION INITIATED: user_id=%s email=%s", uid, user.get("email"))

    background_tasks.add_task(_delete_all_user_data, uid)

    return {
        "ok":      True,
        "message": "Your account and all associated data will be permanently deleted within 24 hours.",
        "user_id": uid,
    }


async def _delete_all_user_data(user_id: str) -> None:
    """Background task: delete all data for a user. Idempotent."""
    collections_to_clear = [
        applications, activity_logs, notifications, xp_events,
        cv_versions, interview_sessions, emails_col, bookmarks,
        ai_usage,
    ]

    for col in collections_to_clear:
        try:
            result = await col.delete_many({"user_id": user_id})
            logger.info("GDPR delete: %s.delete_many(%s) → %d deleted",
                        col.name, user_id, result.deleted_count)
        except Exception as ex:
            logger.error("GDPR delete failed for %s: %s", col.name, ex)

    # Delete referral records
    try:
        await referrals.delete_many({"referrer_id": user_id})
        await referrals.update_many(
            {"pending": user_id},
            {"$pull": {"pending": user_id}},
        )
    except Exception as ex:
        logger.error("GDPR delete referrals failed: %s", ex)

    # Anonymize rather than delete profile (for referral integrity)
    try:
        await profiles.delete_one({"user_id": user_id})
    except Exception:
        pass

    # Delete sessions
    try:
        await mongo_db.sessions.delete_many({"user_id": user_id})
    except Exception:
        pass

    # Finally delete user document
    try:
        await users.delete_one({"user_id": user_id})
    except Exception as ex:
        logger.error("GDPR delete user doc failed: %s", ex)

    logger.warning("GDPR ACCOUNT DELETION COMPLETE: user_id=%s", user_id)


# ─────────────────────────────────────────────
# PRIVACY CONSENT
# ─────────────────────────────────────────────

@router.patch("/consent")
async def update_consent(payload: dict, user=Depends(get_current_user)):
    """Update user's privacy consent flags."""
    uid = user["user_id"]
    allowed = {"marketing_emails", "analytics", "ai_improvement"}
    updates = {k: bool(v) for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid consent flags provided.")
    await users.update_one(
        {"user_id": uid},
        {"$set": {f"consent.{k}": v for k, v in updates.items()}},
    )
    return {"ok": True, "updated": updates}
