"""CV Intelligence: Tailoring, ATS scoring, Cover Letter generation, version history.
All AI calls route through orchestrator.run() for unified persona + memory + telemetry.
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import profiles, jobs, cv_versions
from models import new_id, CVScoreRequest, CoverLetterRequest
from auth import get_current_user
from llm_schemas import parse_llm_json
from orchestrator import orchestrator
from activity import log_activity
from xp import award_xp
from ai_limits import check_ai_quota
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cv", tags=["cv"])


# ─────────────────────────────────────────────
# ATS SCORE
# ─────────────────────────────────────────────

@router.post("/ats-score")
async def ats_score(payload: CVScoreRequest, user=Depends(get_current_user)):
    """Score CV against a job description for ATS compatibility."""
    cv_text  = payload.cv_text or ""
    job_text = payload.job_description or ""
    job_id   = payload.job_id

    if not cv_text or not job_text:
        profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
        cv_text = cv_text or profile.get("cv_text", "")
        if job_id and not job_text:
            job = await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}
            job_text = job.get("description", "")

    if not cv_text:
        raise HTTPException(400, "No CV found. Upload your CV first.")
    if not job_text:
        raise HTTPException(400, "No job description provided.")

    await check_ai_quota(user, "ats_score")

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="cv_ats",
            task="structured",
            feature_prompt=(
                "You are an ATS (Applicant Tracking System) expert. "
                "Analyze the CV against the job description using the user's career context. "
                "Return ONLY valid JSON — no markdown, no prose:\n"
                '{"score": 0-100, '
                '"matching_keywords": ["keyword"], '
                '"missing_keywords": ["keyword"], '
                '"matching_skills": ["skill"], '
                '"missing_skills": ["skill"], '
                '"format_issues": ["issue"], '
                '"strengths": ["strength"], '
                '"improvements": ["specific improvement"], '
                '"summary": "2 sentence verdict"}'
            ),
            user_message=f"JOB DESCRIPTION:\n{job_text[:3000]}\n\nCV:\n{cv_text[:3000]}",
            session_id=f"ats_{user['user_id']}_{new_id('ats')}",
            publish_event="ats_scored",
            event_payload={"job_id": job_id},
        )
        result = parse_llm_json(text)
        result["job_id"]    = job_id
        result["scored_at"] = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as ex:
        logger.error("ats_score failed: %s", ex)
        raise HTTPException(500, "ATS scoring failed. Try again.")


# ─────────────────────────────────────────────
# CV TAILORING
# ─────────────────────────────────────────────

@router.post("/tailor")
async def tailor_cv(payload: dict, user=Depends(get_current_user)):
    """Rewrite CV to match a specific job description. Saves version."""
    job_id   = payload.get("job_id")
    cv_text  = payload.get("cv_text", "")
    job_text = payload.get("job_description", "")

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    cv_text = cv_text or profile.get("cv_text", "")
    if not cv_text:
        raise HTTPException(400, "No CV found. Upload your CV first.")
    if not job_text:
        raise HTTPException(400, "No job description provided.")

    job_doc     = await jobs.find_one({"job_id": job_id}, {"_id": 0}) if job_id else None
    job_title   = (job_doc or {}).get("title")   or payload.get("job_title", "Target Role")
    job_company = (job_doc or {}).get("company") or payload.get("company", "")

    await check_ai_quota(user, "cv_tailor")

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="cv_tailor",
            task="reasoning",
            feature_prompt=(
                "You are an elite CV writer and ATS optimization expert with full knowledge "
                "of this user's career history and goals. "
                "Rewrite the candidate's CV to be perfectly tailored for the target job.\n"
                "Rules:\n"
                "1. Keep ALL real experience and qualifications — never fabricate\n"
                "2. Reorder and reframe existing experience to match job requirements\n"
                "3. Add relevant keywords from job description naturally\n"
                "4. Improve action verbs and quantify where possible\n"
                "5. Remove irrelevant content to make space for relevant items\n"
                "6. Maintain professional tone throughout\n"
                "Return ONLY valid JSON:\n"
                '{"tailored_cv": "full rewritten CV text", '
                '"changes_made": ["change description"], '
                '"keywords_added": ["keyword"], '
                '"ats_improvement": "estimated % improvement", '
                '"tips": ["additional tip"]}'
            ),
            user_message=(
                f"TARGET JOB: {job_title} at {job_company}\n\n"
                f"JOB DESCRIPTION:\n{job_text[:3000]}\n\n"
                f"ORIGINAL CV:\n{cv_text[:3000]}"
            ),
            session_id=f"tailor_{user['user_id']}_{new_id('tlr')}",
            publish_event="cv_tailored",
            event_payload={"job_id": job_id, "job_title": job_title},
        )
        result = parse_llm_json(text)

        version_id = new_id("cvv")
        await cv_versions.insert_one({
            "version_id":     version_id,
            "user_id":        user["user_id"],
            "job_id":         job_id,
            "job_title":      job_title,
            "job_company":    job_company,
            "original_cv":    cv_text,
            "tailored_cv":    result.get("tailored_cv", ""),
            "changes_made":   result.get("changes_made", []),
            "keywords_added": result.get("keywords_added", []),
            "created_at":     datetime.now(timezone.utc).isoformat(),
        })

        await log_activity(
            user["user_id"], "cv_tailored",
            f"CV tailored for {job_title}",
            f"CV optimized for {job_title} at {job_company}",
            {"job_id": job_id, "version_id": version_id},
        )
        await award_xp(user["user_id"], "cv_tailored")

        result["version_id"] = version_id
        return result

    except Exception as ex:
        logger.error("tailor_cv failed: %s", ex)
        raise HTTPException(500, "CV tailoring failed. Try again.")


# ─────────────────────────────────────────────
# COVER LETTER GENERATOR
# ─────────────────────────────────────────────

@router.post("/cover-letter")
async def generate_cover_letter(payload: CoverLetterRequest, user=Depends(get_current_user)):
    """Generate a tailored cover letter for a specific job."""
    job_id   = payload.job_id
    tone     = payload.tone or "professional"
    language = "en"

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    cv_text = profile.get("cv_text", "")
    name    = profile.get("full_name", "")

    if not cv_text:
        raise HTTPException(400, "No CV found. Upload your CV first.")

    await check_ai_quota(user, "cover_letter")
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}

    job_title   = job.get("title")       or payload.job_title or ""
    job_company = job.get("company")     or payload.company or ""
    job_text    = job.get("description") or payload.job_description or ""

    lang_instruction = {
        "ar": "Write the cover letter in Arabic (Modern Standard Arabic).",
        "pt": "Write the cover letter in European Portuguese.",
        "en": "Write the cover letter in English.",
    }.get(language, "Write in English.")

    tone_instruction = {
        "professional": "Use a professional, confident tone.",
        "enthusiastic": "Show genuine enthusiasm and passion.",
        "concise":      "Keep it short — 3 paragraphs maximum, no filler.",
    }.get(tone, "Professional tone.")

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="cv_cover_letter",
            task="reasoning",
            feature_prompt=(
                f"You are an expert career coach writing cover letters for this specific user. "
                f"You know their full career history — use it. "
                f"{lang_instruction} {tone_instruction}\n"
                "Write a cover letter that:\n"
                "1. Opens with a compelling hook that references this user's real background\n"
                "2. Connects their specific experience to the job requirements\n"
                "3. Shows knowledge of the company\n"
                "4. Ends with a confident call to action\n"
                "Return ONLY valid JSON:\n"
                '{"cover_letter": "full cover letter text", '
                '"subject_line": "email subject line", '
                '"key_points": ["main selling point"]}'
            ),
            user_message=(
                f"CANDIDATE NAME: {name}\n\n"
                f"TARGET ROLE: {job_title} at {job_company}\n\n"
                f"JOB DESCRIPTION:\n{job_text[:2000]}\n\n"
                f"CV SUMMARY:\n{cv_text[:2000]}"
            ),
            session_id=f"covltr_{user['user_id']}_{new_id('cl')}",
            publish_event="cover_letter_generated",
            event_payload={"job_id": job_id},
        )
        result = parse_llm_json(text)
        result["job_id"]   = job_id
        result["language"] = language
        result["tone"]     = tone
        return result

    except Exception as ex:
        logger.error("cover_letter failed: %s", ex)
        raise HTTPException(500, "Cover letter generation failed.")


# ─────────────────────────────────────────────
# VERSION HISTORY
# ─────────────────────────────────────────────

@router.get("/versions")
async def list_cv_versions(user=Depends(get_current_user), limit: int = 20):
    """List all tailored CV versions for the current user."""
    docs = await cv_versions.find(
        {"user_id": user["user_id"]}, {"_id": 0, "original_cv": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"versions": docs, "count": len(docs)}


@router.get("/versions/{version_id}")
async def get_cv_version(version_id: str, user=Depends(get_current_user)):
    """Get a specific CV version."""
    doc = await cv_versions.find_one(
        {"version_id": version_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "CV version not found.")
    return doc


@router.delete("/versions/{version_id}")
async def delete_cv_version(version_id: str, user=Depends(get_current_user)):
    r = await cv_versions.delete_one(
        {"version_id": version_id, "user_id": user["user_id"]}
    )
    if r.deleted_count == 0:
        raise HTTPException(404, "CV version not found.")
    return {"ok": True}


# ─────────────────────────────────────────────
# AI USAGE SUMMARY
# ─────────────────────────────────────────────

@router.get("/usage")
async def ai_usage_summary(user=Depends(get_current_user)):
    """Return today's AI usage across all features for the current user."""
    from ai_limits import get_ai_usage_summary
    from quota import get_effective_plan
    plan = await get_effective_plan(user)
    if user.get("trial_active"):
        plan = "pro"
    summary = await get_ai_usage_summary(user["user_id"], plan)
    return {"plan": plan, "usage": summary, "trial_active": bool(user.get("trial_active"))}
