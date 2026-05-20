"""Chrome Extension API — receives jobs saved from browser."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import jobs as jobs_col, applications, profiles
from models import new_id
from auth import get_current_user
from job_sources import _content_hash, _normalize, _extract_skills, _guess_seniority
from activity import log_activity
from xp import award_xp
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/extension", tags=["extension"])


@router.post("/save-job")
async def extension_save_job(payload: dict, user=Depends(get_current_user)):
    """
    Save a job from the Chrome Extension.
    Deduplicates, inserts to jobs collection, optionally creates application.
    """
    title      = (payload.get("title") or "").strip()
    company    = (payload.get("company") or "").strip()
    location   = (payload.get("location") or "").strip()
    source_url = (payload.get("source_url") or "").strip()
    description = payload.get("description") or ""
    source     = payload.get("source") or "extension"

    if not title or not source_url:
        raise HTTPException(400, "title and source_url are required.")

    # Build normalized job doc
    content_hash = _content_hash(title, company, location, source_url)

    # Deduplication
    existing = await jobs_col.find_one({"content_hash": content_hash}, {"_id": 0, "job_id": 1})
    if existing:
        job_id = existing["job_id"]
    else:
        job_doc = {
            "job_id":         new_id("job"),
            "title":          title,
            "company":        company,
            "location":       location,
            "remote":         "remote" in location.lower() or payload.get("remote", False),
            "source":         source,
            "source_url":     source_url,
            "description":    description[:5000],
            "skills_required": _extract_skills(description),
            "seniority":      _guess_seniority(title),
            "salary_range":   payload.get("salary_range"),
            "salary_min":     None,
            "salary_max":     None,
            "content_hash":   content_hash,
            "posted_at":      datetime.now(timezone.utc).isoformat(),
            "saved_by_extension": True,
        }
        await jobs_col.insert_one(job_doc)
        job_id = job_doc["job_id"]

    # Auto-create "discovered" application so it appears in pipeline
    existing_app = await applications.find_one(
        {"user_id": user["user_id"], "job_id": job_id}, {"_id": 0, "application_id": 1}
    )
    if not existing_app:
        app = {
            "application_id": new_id("app"),
            "user_id":        user["user_id"],
            "job_id":         job_id,
            "status":         "discovered",
            "timeline":       [{"status": "discovered", "timestamp": datetime.now(timezone.utc).isoformat()}],
            "notes":          "",
            "created_at":     datetime.now(timezone.utc).isoformat(),
            "updated_at":     datetime.now(timezone.utc).isoformat(),
        }
        await applications.insert_one(app)

    # Log + XP
    await log_activity(
        user["user_id"], "job_saved",
        f"Saved {title} from {source}",
        f"Saved {title} at {company} via Chrome Extension.",
        {"job_id": job_id, "source": source, "company": company},
    )
    await award_xp(user["user_id"], "job_saved")

    return {
        "ok":    True,
        "job_id": job_id,
        "title": title,
        "company": company,
        "already_existed": bool(existing),
        "xp_awarded": 10,
    }
