"""Jobs, applications, decision engine routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone
from db import jobs, applications, profiles, decisions, bookmarks
from models import new_id
from auth import get_current_user
from llm_service import llm_call, parse_json_loose
from job_sources import ingest_remotive, ingest_all
from quota import (
    get_effective_plan,
    get_match_usage,
    increment_match_usage,
    usage_summary,
    FREE_MATCH_LIMIT,
)

router = APIRouter(prefix="/api", tags=["jobs"])


async def _log(user_id: str, event_type: str, title: str, description: str, metadata: dict | None = None):
    """Fire-and-forget activity log helper."""
    try:
        from routes_activity import log_activity
        await log_activity(user_id, event_type, title, description, metadata)
    except Exception:
        pass


def _skill_overlap_score(cv_skills: list, job_skills: list) -> int:
    if not job_skills:
        return 50
    cv_set = {s.lower() for s in cv_skills}
    job_set = {s.lower() for s in job_skills}
    overlap = len(cv_set & job_set)
    return min(100, int(100 * overlap / max(1, len(job_set))))


@router.get("/jobs")
async def list_jobs(
    user=Depends(get_current_user),
    q: Optional[str] = None,
    remote_only: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    query = {}
    if remote_only:
        query["remote"] = True
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"company": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    total = await jobs.count_documents(query)
    skip = (page - 1) * size
    docs = await jobs.find(query, {"_id": 0}).skip(skip).limit(size).to_list(size)
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    cv_skills = profile.get("skills", []) if profile else []
    for d in docs:
        d["quick_score"] = _skill_overlap_score(cv_skills, d.get("skills_required", []))
    docs.sort(key=lambda x: -x["quick_score"])
    pages = max(1, (total + size - 1) // size)
    return {
        "jobs": docs,
        "count": len(docs),
        "pagination": {
            "page": page, "size": size, "total": total,
            "pages": pages, "has_next": page < pages, "has_prev": page > 1,
        },
    }


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, user=Depends(get_current_user)):
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    app_doc = await applications.find_one(
        {"user_id": user["user_id"], "job_id": job_id}, {"_id": 0}
    )
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    cv_skills = profile.get("skills", []) if profile else []
    job["quick_score"] = _skill_overlap_score(cv_skills, job.get("skills_required", []))
    return {"job": job, "application": app_doc}


@router.post("/jobs/{job_id}/match")
async def compute_match(job_id: str, user=Depends(get_current_user)):
    """Use Claude to compute deep match analysis with reasoning."""
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile or not profile.get("cv_text"):
        raise HTTPException(400, "Upload your CV first")

    # Cache check (returning cached doesn't consume quota)
    cached = await decisions.find_one(
        {"user_id": user["user_id"], "job_id": job_id, "type": "match"},
        {"_id": 0},
    )
    if cached:
        return cached["result"]

    # Quota check — free users limited to FREE_MATCH_LIMIT new matches per month
    plan = await get_effective_plan(user)
    if plan == "free":
        used = await get_match_usage(user["user_id"])
        if used >= FREE_MATCH_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "quota_exceeded",
                    "message": f"You've used all {FREE_MATCH_LIMIT} free matches this month. Upgrade to Pro for unlimited matching.",
                    "matches_used": used,
                    "matches_limit": FREE_MATCH_LIMIT,
                    "upgrade_url": "/pricing",
                },
            )

    system = (
        "You are an elite career strategist AI. Given a candidate's CV and a job, "
        "produce a structured match analysis. Be honest and decisive. "
        "Return ONLY valid JSON, no prose. Schema: "
        '{"score": int 0-100, "confidence": int 0-100, '
        '"decision": "apply"|"consider"|"skip", '
        '"reasoning": "2-3 sentence rationale", '
        '"strengths": ["..."], "gaps": ["..."], '
        '"expected_outcome": "what likely happens if they apply"}'
    )
    user_prompt = (
        f"CANDIDATE CV:\n{profile['cv_text']}\n\n"
        f"JOB:\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Seniority: {job['seniority']}\nLocation: {job['location']}\n"
        f"Required skills: {', '.join(job.get('skills_required', []))}\n\n"
        f"Description: {job['description']}\n\n"
        "Output JSON only."
    )
    try:
        text = await llm_call(
            task="reasoning",
            system=system,
            user=user_prompt,
            session_id=f"match_{user['user_id']}_{job_id}",
        )
        data = parse_json_loose(text)
        if not data or "score" not in data:
            raise ValueError("bad llm output")
    except Exception:
        # heuristic fallback
        cv_skills = profile.get("skills", [])
        score = _skill_overlap_score(cv_skills, job.get("skills_required", []))
        data = {
            "score": score,
            "confidence": 60,
            "decision": "consider" if score >= 50 else "skip",
            "reasoning": f"Skill overlap is {score}%. Heuristic fallback (LLM unavailable).",
            "strengths": list(set(cv_skills) & set(job.get("skills_required", []))),
            "gaps": list(set(job.get("skills_required", [])) - set(cv_skills)),
            "expected_outcome": "Apply if you can address the listed gaps in your application.",
        }

    await decisions.update_one(
        {"user_id": user["user_id"], "job_id": job_id, "type": "match"},
        {"$set": {
            "user_id": user["user_id"],
            "job_id": job_id,
            "type": "match",
            "result": data,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Count the match against quota only for free users (cached returns above don't count)
    if plan == "free":
        await increment_match_usage(user["user_id"])

    return data


@router.get("/me/usage")
async def my_usage(user=Depends(get_current_user)):
    """Returns current month's usage + quota state. Used by frontend banners."""
    return await usage_summary(user)


@router.post("/jobs/ingest")
async def ingest_jobs(payload: dict = None, user=Depends(get_current_user)):
    """Pull real jobs from all configured sources (Adzuna pt+gb, Jooble, Remotive) with dedupe.
    Pass {"source": "remotive"} for legacy single-source behavior."""
    payload = payload or {}
    query = (payload.get("query") or "").strip()
    limit = min(int(payload.get("limit") or 25), 50)
    source = (payload.get("source") or "all").lower()
    try:
        if source == "remotive":
            return await ingest_remotive(query=query, limit=limit)
        return await ingest_all(query=query, limit_per_source=limit)
    except Exception as ex:
        raise HTTPException(502, f"Job ingest failed: {ex}")



@router.get("/applications")
async def list_applications(user=Depends(get_current_user)):
    docs = await applications.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(500)
    # attach job info
    job_ids = [d["job_id"] for d in docs]
    job_map = {}
    if job_ids:
        async for j in jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0}):
            job_map[j["job_id"]] = j
    for d in docs:
        d["job"] = job_map.get(d["job_id"])
    docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"applications": docs, "count": len(docs)}


@router.post("/applications")
async def create_application(payload: dict, user=Depends(get_current_user)):
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id required")
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")

    existing = await applications.find_one(
        {"user_id": user["user_id"], "job_id": job_id}, {"_id": 0}
    )
    if existing:
        return existing

    now = datetime.now(timezone.utc).isoformat()
    app = {
        "application_id": new_id("app"),
        "user_id": user["user_id"],
        "job_id": job_id,
        "status": "applied",
        "timeline": [
            {"status": "discovered", "timestamp": now, "reason": "Saved by user", "confidence": 100},
            {"status": "applied", "timestamp": now, "reason": "User submitted application", "confidence": 100},
        ],
        "match": payload.get("match"),
        "notes": payload.get("notes", ""),
        "created_at": now,
        "updated_at": now,
    }
    await applications.insert_one(app)
    app.pop("_id", None)
    # Log activity
    await _log(user["user_id"], "job_applied",
               f"Applied to {job['title']}",
               f"Applied to {job['title']} at {job['company']}",
               {"job_id": job_id, "company": job["company"]})
    # Publish into orchestration bus (fire-and-forget — never blocks the response)
    try:
        from event_bus import event_bus
        await event_bus.publish("job_applied", user["user_id"], {
            "job_id": job_id,
            "job_title": job.get("title"),
            "company": job.get("company"),
        })
    except Exception:
        pass
    return app


@router.patch("/applications/{application_id}")
async def update_application_status(
    application_id: str, payload: dict, user=Depends(get_current_user)
):
    new_status = payload.get("status")
    reason = payload.get("reason", "Status updated")
    if new_status not in ["discovered", "applied", "under_review", "interview", "offer", "rejected"]:
        raise HTTPException(400, "Invalid status")

    app = await applications.find_one(
        {"application_id": application_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not app:
        raise HTTPException(404, "Application not found")

    now = datetime.now(timezone.utc).isoformat()
    timeline = app.get("timeline", [])
    timeline.append({"status": new_status, "timestamp": now, "reason": reason, "confidence": payload.get("confidence", 100)})

    await applications.update_one(
        {"application_id": application_id},
        {"$set": {"status": new_status, "timeline": timeline, "updated_at": now}},
    )
    # Log activity + award XP for meaningful transitions
    job_doc = await jobs.find_one({"job_id": app["job_id"]}, {"_id": 0}) or {}
    await _log(user["user_id"], "status_changed",
               f"Application moved to {new_status.replace('_', ' ').title()}",
               f"{job_doc.get('title', 'Job')} at {job_doc.get('company', '?')} → {new_status}",
               {"application_id": application_id, "old_status": app.get("status"), "new_status": new_status})
    # Award XP via xp engine
    xp_map = {"applied": "job_applied", "under_review": "status_under_review",
              "interview": "status_interview", "offer": "status_offer"}
    if new_status in xp_map:
        try:
            from xp import award_xp
            await award_xp(user["user_id"], xp_map[new_status])
        except Exception:
            pass
    # Publish status-change events into the orchestration bus
    try:
        from event_bus import event_bus
        status_event_map = {
            "rejected": "job_rejected",
            "offer":    "offer_received",
            "interview": "interview_scheduled",
        }
        bus_event = status_event_map.get(new_status)
        if bus_event:
            await event_bus.publish(bus_event, user["user_id"], {
                "application_id": application_id,
                "job_id":        app["job_id"],
                "job_title":     job_doc.get("title"),
                "company":       job_doc.get("company"),
                "old_status":    app.get("status"),
                "new_status":    new_status,
            })
    except Exception:
        pass
    updated = await applications.find_one({"application_id": application_id}, {"_id": 0})
    return updated


@router.get("/decisions/recommendations")
async def smart_recommendations(user=Depends(get_current_user), limit: int = 5):
    """Decision Engine: returns top jobs to apply for, with reasoning."""
    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not profile:
        return {"recommendations": []}
    cv_skills = profile.get("skills", [])
    target_seniorities = []
    yrs = profile.get("years_experience") or 0
    if yrs < 3:
        target_seniorities = ["junior", "mid"]
    elif yrs < 7:
        target_seniorities = ["mid", "senior"]
    else:
        target_seniorities = ["senior", "lead"]

    # Fetch jobs not yet applied
    applied_ids = [a["job_id"] async for a in applications.find({"user_id": user["user_id"]}, {"_id": 0, "job_id": 1})]
    pool = await jobs.find(
        {"job_id": {"$nin": applied_ids}, "seniority": {"$in": target_seniorities}}, {"_id": 0}
    ).to_list(50)

    scored = []
    for j in pool:
        score = _skill_overlap_score(cv_skills, j.get("skills_required", []))
        # ROI: reward higher score, penalize lead roles slightly if user "avoids difficult"
        roi = score
        if profile.get("behavior", {}).get("avoids_lead_roles") and j.get("seniority") == "lead":
            roi -= 15
        scored.append({**j, "quick_score": score, "roi": roi})
    scored.sort(key=lambda x: -x["roi"])
    top = scored[:limit]
    for t in top:
        decision = "apply" if t["roi"] >= 60 else ("consider" if t["roi"] >= 40 else "skip")
        t["decision"] = {
            "decision": decision,
            "confidence": min(95, 50 + t["roi"] // 2),
            "reason": f"Skill match {t['quick_score']}%, seniority fit, ROI {t['roi']}.",
            "expected_outcome": (
                "High response likelihood — strong on core stack."
                if decision == "apply"
                else "Moderate — gaps may need narrative cover."
                if decision == "consider"
                else "Low — significant skill or seniority gap."
            ),
        }
    return {"recommendations": top}

# ─────────────────────────────────────────────
# BOOKMARKS
# ─────────────────────────────────────────────

@router.post("/bookmarks/{job_id}")
async def bookmark_job(job_id: str, user=Depends(get_current_user)):
    """Bookmark a job for later review."""
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    now = datetime.now(timezone.utc).isoformat()
    try:
        await bookmarks.insert_one({
            "bookmark_id": new_id("bkm"),
            "user_id": user["user_id"],
            "job_id": job_id,
            "created_at": now,
        })
        await _log(user["user_id"], "job_saved", f"Bookmarked {job['title']}",
                   f"Saved {job['title']} at {job['company']}", {"job_id": job_id})
        # Publish bookmark event (cross-feature CV-tailor pre-warm)
        try:
            from event_bus import event_bus
            await event_bus.publish("bookmark_added", user["user_id"], {
                "job_id": job_id,
                "job_title": job.get("title"),
                "company": job.get("company"),
            })
        except Exception:
            pass
    except Exception:
        pass  # Duplicate — already bookmarked
    return {"ok": True, "job_id": job_id}


@router.delete("/bookmarks/{job_id}")
async def remove_bookmark(job_id: str, user=Depends(get_current_user)):
    await bookmarks.delete_one({"user_id": user["user_id"], "job_id": job_id})
    return {"ok": True}


@router.get("/bookmarks")
async def list_bookmarks(user=Depends(get_current_user)):
    docs = await bookmarks.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    job_ids = [d["job_id"] for d in docs]
    job_map = {}
    if job_ids:
        async for j in jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0}):
            job_map[j["job_id"]] = j
    result = []
    for d in docs:
        if d["job_id"] in job_map:
            result.append({**d, "job": job_map[d["job_id"]]})
    return {"bookmarks": result, "count": len(result)}


# ─────────────────────────────────────────────
# APPLICATION NOTES AUTOSAVE
# ─────────────────────────────────────────────

@router.patch("/applications/{application_id}/notes")
async def update_notes(application_id: str, payload: dict, user=Depends(get_current_user)):
    """Autosave notes for an application."""
    app = await applications.find_one(
        {"application_id": application_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not app:
        raise HTTPException(404, "Application not found")
    notes = payload.get("notes", "")
    await applications.update_one(
        {"application_id": application_id},
        {"$set": {"notes": notes, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "notes": notes}
