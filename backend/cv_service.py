"""Shared CV service layer — eliminates duplication between routes_cv.py and routes_cv_intel.py.

Both route files use the same core logic for ATS scoring, tailoring, and cover letter.
This module centralises that logic and is imported by both.
"""
import logging
from typing import Optional

from db import profiles, jobs
from ai_limits import check_ai_quota
from llm_service import llm_call
from llm_schemas import parse_llm_json, ATSScoreOutput, CoverLetterOutput
from orchestrator import orchestrator

logger = logging.getLogger(__name__)


async def get_user_cv(user_id: str) -> tuple[str, dict]:
    """Return (cv_text, profile_doc) for a user. Raises ValueError if CV missing."""
    profile = await profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    cv_text = profile.get("cv_text", "").strip()
    if not cv_text:
        raise ValueError("No CV found. Upload your CV first.")
    return cv_text, profile


async def get_job_doc(job_id: Optional[str]) -> dict:
    """Return job doc or empty dict if not found."""
    if not job_id:
        return {}
    return await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}


async def run_ats_score(
    user: dict,
    cv_text: str,
    job_text: str,
    job_id: Optional[str] = None,
) -> dict:
    """Core ATS scoring logic. Used by both cv and cv-intel routes."""
    await check_ai_quota(user, "ats_score")

    system = (
        "You are an expert ATS (Applicant Tracking System) analyst. "
        "Analyse the CV against the job description and return a JSON object with: "
        "score (0-100), matching_keywords (list), missing_keywords (list), "
        "matching_skills (list), missing_skills (list), format_issues (list), "
        "strengths (list), improvements (list), summary (string)."
    )
    from prompt_guard import build_safe_prompt
    safe_prompt = build_safe_prompt({
        "job_description": (job_text, 3000),
        "candidate_cv":    (cv_text, 3000),
    })

    raw = await llm_call(
        "ats_score",
        system=system,
        user=safe_prompt,
        session_id=f"ats_{user['user_id']}_{job_id or 'none'}",
    )
    return parse_llm_json(raw, ATSScoreOutput)


async def run_cv_tailor(
    user: dict,
    cv_text: str,
    job_doc: dict,
    job_id: str,
) -> dict:
    """Core CV tailoring logic. Used by both cv and cv-intel routes."""
    await check_ai_quota(user, "cv_tailor")

    job_title   = job_doc.get("title", "")
    job_company = job_doc.get("company", "")
    job_text    = job_doc.get("description", "")[:3000]

    raw = await orchestrator.run(
        "cv_tailor",
        user_id=user["user_id"],
        job_id=job_id,
        extra={
            "cv_text": cv_text[:3000],
            "job_title": job_title,
            "job_company": job_company,
            "job_description": job_text,
        },
        session_id=f"tailor_{user['user_id']}_{job_id}",
    )
    return parse_llm_json(raw)


async def run_cover_letter(
    user: dict,
    cv_text: str,
    job_doc: dict,
    job_title: str = "",
    job_company: str = "",
    job_description: str = "",
    tone: str = "professional",
    language: str = "en",
) -> dict:
    """Core cover letter generation. Used by both cv and cv-intel routes."""
    await check_ai_quota(user, "cover_letter")

    lang_map = {
        "ar": "Write the cover letter in Arabic (Modern Standard Arabic).",
        "pt": "Write the cover letter in European Portuguese.",
        "en": "Write the cover letter in English.",
    }
    lang_instruction = lang_map.get(language, "Write in English.")

    j_title   = job_doc.get("title")       or job_title   or "Target Role"
    j_company = job_doc.get("company")     or job_company or ""
    j_text    = job_doc.get("description") or job_description or ""

    system = (
        f"You are an expert career coach. Write a compelling cover letter. "
        f"Tone: {tone}. {lang_instruction} "
        "Return JSON: {letter: string, subject: string}"
    )
    user_prompt = (
        f"Job: {j_title} at {j_company}\n\n"
        f"Job Description:\n{j_text[:2000]}\n\n"
        f"CV:\n{cv_text[:2500]}"
    )

    raw = await llm_call(
        "cover_letter",
        system=system,
        user=user_prompt,
        session_id=f"cover_{user['user_id']}",
    )
    return parse_llm_json(raw, CoverLetterOutput)
