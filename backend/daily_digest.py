"""Daily job-match digest runner.

Called by an external cron (e.g. cron-job.org) hitting /api/internal/run-daily-digest.
For each user with daily_matches=True who hasn't been emailed in ≥20 hours:
  1. Pull fresh jobs via ingest_all(query=top_skill)
  2. Compute quick_score against user's CV skills
  3. Pick top 3 NEW jobs (job_id NOT in prior applications/decisions)
  4. Send Resend email with html + text
  5. Update profile.last_email_sent
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from db import profiles, users, jobs as jobs_col, applications, decisions
from job_sources import ingest_all
from emailer import send_email, render_daily_digest

log = logging.getLogger("daily_digest")

DASHBOARD_URL_FALLBACK = "https://job-agent-ai-6.preview.emergentagent.com"


def _quick_score(cv_skills: list, job_skills: list) -> int:
    if not job_skills:
        return 50
    cv = {s.lower() for s in cv_skills}
    jb = {s.lower() for s in job_skills}
    return min(100, int(100 * len(cv & jb) / max(1, len(jb))))


async def _pick_top_jobs(profile: dict, exclude_job_ids: set, limit: int = 3) -> List[Dict[str, Any]]:
    cv_skills = profile.get("skills", [])
    cursor = jobs_col.find(
        {"job_id": {"$nin": list(exclude_job_ids)}, "source": {"$ne": "mock"}},
        {"_id": 0},
    ).limit(200)
    scored = []
    async for j in cursor:
        score = _quick_score(cv_skills, j.get("skills_required", []))
        if score >= 40:
            scored.append({**j, "quick_score": score})
    scored.sort(key=lambda x: -x["quick_score"])
    return scored[:limit]


async def run_daily_digest_for_user(user_doc: dict, dashboard_url: str = DASHBOARD_URL_FALLBACK) -> dict:
    """Send digest for one user. Returns status dict."""
    user_id = user_doc["user_id"]
    profile = await profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not profile:
        return {"user_id": user_id, "skipped": True, "reason": "no profile"}
    if not profile.get("daily_matches"):
        return {"user_id": user_id, "skipped": True, "reason": "daily_matches OFF"}

    # 20-hour gate to avoid duplicate sends if cron runs more frequently
    last_sent_raw = profile.get("last_email_sent")
    if last_sent_raw:
        try:
            last_sent = datetime.fromisoformat(last_sent_raw)
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - last_sent < timedelta(hours=20):
                return {"user_id": user_id, "skipped": True, "reason": "last_email_sent < 20h"}
        except Exception:
            pass

    # Refresh job pool keyed on user's top skill
    skills = profile.get("skills", [])
    top_skill = skills[0] if skills else ""
    try:
        await ingest_all(query=top_skill, limit_per_source=10)
    except Exception as ex:
        log.warning("digest: ingest failed for %s: %s", user_id, ex)

    # Exclude jobs the user already engaged with
    applied = [a["job_id"] async for a in applications.find({"user_id": user_id}, {"_id": 0, "job_id": 1})]
    decided = [d["job_id"] async for d in decisions.find({"user_id": user_id}, {"_id": 0, "job_id": 1})]
    exclude = set(applied) | set(decided)

    top = await _pick_top_jobs(profile, exclude, limit=3)
    if not top:
        return {"user_id": user_id, "skipped": True, "reason": "no matching jobs"}

    html, text = render_daily_digest(
        user_name=user_doc.get("name", ""),
        jobs=top,
        dashboard_url=dashboard_url,
    )
    result = await send_email(
        to=user_doc["email"],
        subject="3 new jobs match your CV today",
        html=html,
        text=text,
    )

    if result.get("sent"):
        await profiles.update_one(
            {"user_id": user_id},
            {"$set": {"last_email_sent": datetime.now(timezone.utc).isoformat()}},
        )
    return {"user_id": user_id, "email": user_doc["email"], "jobs_sent": len(top), **result}


async def run_daily_digest_all(dashboard_url: str = DASHBOARD_URL_FALLBACK) -> dict:
    """Iterate every user with daily_matches=True, send digests."""
    opted_in_user_ids = [p["user_id"] async for p in profiles.find({"daily_matches": True}, {"_id": 0, "user_id": 1})]
    log.info("digest: %d users opted in", len(opted_in_user_ids))
    if not opted_in_user_ids:
        return {"users_processed": 0, "results": []}

    results = []
    async for u in users.find({"user_id": {"$in": opted_in_user_ids}}, {"_id": 0}):
        try:
            r = await run_daily_digest_for_user(u, dashboard_url=dashboard_url)
        except Exception as ex:
            log.exception("digest failed for %s", u.get("user_id"))
            r = {"user_id": u.get("user_id"), "error": str(ex)}
        results.append(r)

    sent_count = sum(1 for r in results if r.get("sent"))
    skipped_count = sum(1 for r in results if r.get("skipped"))
    return {
        "users_processed": len(results),
        "sent": sent_count,
        "skipped": skipped_count,
        "results": results,
    }
