"""CV Intelligence — Tailoring, Cover Letter, ATS Score, Interview Prep."""
from fastapi import APIRouter, Depends, HTTPException
from db import profiles, jobs
from auth import get_current_user
from llm_service import llm_call, parse_json_loose
from activity import log_activity
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cv-intel", tags=["cv-intelligence"])


async def _get_profile_and_job(user_id: str, job_id: str) -> tuple[dict, dict]:
    profile = await profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not profile or not profile.get("cv_text"):
        raise HTTPException(400, "Upload your CV first before using CV Intelligence.")
    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found.")
    return profile, job


# ─────────────────────────────────────────────
# CV TAILORING
# ─────────────────────────────────────────────

@router.post("/tailor/{job_id}")
async def tailor_cv(job_id: str, user=Depends(get_current_user)):
    """
    Rewrite CV to match a specific job description.
    Returns tailored CV text + list of changes made.
    """
    profile, job = await _get_profile_and_job(user["user_id"], job_id)

    system = (
        "You are an elite CV strategist. Tailor the candidate's CV to match "
        "the job description. Rules: "
        "1) Keep all factual information — do NOT invent experience. "
        "2) Reorder bullet points to surface most relevant experience first. "
        "3) Mirror the job description's keywords and terminology where truthful. "
        "4) Remove or deprioritize irrelevant sections. "
        "5) Keep the same CV structure. "
        "Return ONLY valid JSON: "
        '{"tailored_cv": "full rewritten CV text", '
        '"changes": ["change 1", "change 2"], '
        '"keywords_added": ["keyword1", "keyword2"], '
        '"ats_improvement": "brief explanation of ATS improvements"}'
    )

    user_prompt = (
        f"JOB TITLE: {job.get('title')}\n"
        f"COMPANY: {job.get('company')}\n"
        f"JOB DESCRIPTION:\n{job.get('description', '')[:3000]}\n\n"
        f"REQUIRED SKILLS: {', '.join(job.get('skills_required', []))}\n\n"
        f"CANDIDATE CV:\n{profile.get('cv_text', '')[:4000]}"
    )

    try:
        raw = await llm_call(
            task="reasoning",
            system=system,
            user=user_prompt,
            session_id=f"tailor_{user['user_id']}_{job_id}",
        )
        result = parse_json_loose(raw)
    except Exception as ex:
        logger.error("tailor_cv failed: %s", ex)
        raise HTTPException(500, "CV tailoring failed. Please try again.")

    await log_activity(
        user["user_id"], "cv_tailored",
        f"CV tailored for {job.get('title')} at {job.get('company')}",
        f"Generated tailored CV with {len(result.get('changes', []))} improvements.",
        {"job_id": job_id, "keywords_added": result.get("keywords_added", [])},
    )

    return {
        "tailored_cv":    result.get("tailored_cv", ""),
        "changes":        result.get("changes", []),
        "keywords_added": result.get("keywords_added", []),
        "ats_improvement": result.get("ats_improvement", ""),
        "job_id":         job_id,
        "job_title":      job.get("title"),
        "company":        job.get("company"),
    }


# ─────────────────────────────────────────────
# COVER LETTER GENERATOR
# ─────────────────────────────────────────────

@router.post("/cover-letter/{job_id}")
async def generate_cover_letter(
    job_id: str,
    payload: dict | None = None,
    user=Depends(get_current_user),
):
    """
    Generate a tailored cover letter for a specific job.
    Optional payload: {"tone": "professional|conversational|bold", "highlight": "what to emphasize"}
    """
    profile, job = await _get_profile_and_job(user["user_id"], job_id)

    if payload is None:
        payload = {}
    tone      = (payload.get("tone") or "professional").lower()
    highlight = payload.get("highlight") or ""

    system = (
        f"You are an expert cover letter writer. Write a compelling, {tone} cover letter. "
        "Rules: "
        "1) Never make up experience — only use what's in the CV. "
        "2) Open with a strong hook that is NOT 'I am writing to apply'. "
        "3) Connect 2-3 specific CV achievements to job requirements. "
        "4) Show genuine interest in the company and role. "
        "5) End with a clear, confident call to action. "
        "6) Length: 3-4 paragraphs, max 350 words. "
        "Return ONLY valid JSON: "
        '{"cover_letter": "full cover letter text", '
        '"subject_line": "email subject line for the application", '
        '"key_points": ["point 1", "point 2", "point 3"]}'
    )

    user_prompt = (
        f"JOB: {job.get('title')} at {job.get('company')}\n"
        f"LOCATION: {job.get('location')}\n"
        f"JOB DESCRIPTION:\n{job.get('description', '')[:2000]}\n\n"
        f"CANDIDATE CV:\n{profile.get('cv_text', '')[:3000]}\n\n"
        + (f"HIGHLIGHT: {highlight}\n" if highlight else "")
        + f"TONE REQUESTED: {tone}"
    )

    try:
        raw = await llm_call(
            task="reasoning",
            system=system,
            user=user_prompt,
            session_id=f"cover_{user['user_id']}_{job_id}",
        )
        result = parse_json_loose(raw)
    except Exception as ex:
        logger.error("cover_letter failed: %s", ex)
        raise HTTPException(500, "Cover letter generation failed. Please try again.")

    await log_activity(
        user["user_id"], "cover_letter_generated",
        f"Cover letter for {job.get('title')} at {job.get('company')}",
        "Generated a tailored cover letter.",
        {"job_id": job_id, "tone": tone},
    )

    return {
        "cover_letter": result.get("cover_letter", ""),
        "subject_line": result.get("subject_line", f"Application: {job.get('title')}"),
        "key_points":   result.get("key_points", []),
        "tone":         tone,
        "job_id":       job_id,
        "job_title":    job.get("title"),
        "company":      job.get("company"),
    }


# ─────────────────────────────────────────────
# ATS SCORE CHECKER
# ─────────────────────────────────────────────

@router.post("/ats-score/{job_id}")
async def ats_score(job_id: str, user=Depends(get_current_user)):
    """
    Score the CV against the job description for ATS compatibility.
    Returns score, keyword gaps, and improvement suggestions.
    """
    profile, job = await _get_profile_and_job(user["user_id"], job_id)

    system = (
        "You are an ATS (Applicant Tracking System) expert. Analyze how well "
        "the CV matches the job description for ATS systems. "
        "Return ONLY valid JSON: "
        '{"ats_score": 0-100, '
        '"keyword_match_rate": 0-100, '
        '"present_keywords": ["keyword1"], '
        '"missing_keywords": ["keyword1"], '
        '"format_issues": ["issue1"], '
        '"improvements": ["specific action to take"], '
        '"overall_verdict": "one sentence summary"}'
    )

    user_prompt = (
        f"JOB TITLE: {job.get('title')}\n"
        f"REQUIRED SKILLS: {', '.join(job.get('skills_required', []))}\n"
        f"JOB DESCRIPTION:\n{job.get('description', '')[:2500]}\n\n"
        f"CV:\n{profile.get('cv_text', '')[:3500]}"
    )

    try:
        raw = await llm_call(
            task="fast",
            system=system,
            user=user_prompt,
            session_id=f"ats_{user['user_id']}_{job_id}",
        )
        result = parse_json_loose(raw)
    except Exception as ex:
        logger.error("ats_score failed: %s", ex)
        raise HTTPException(500, "ATS scoring failed. Please try again.")

    return {
        "ats_score":         result.get("ats_score", 0),
        "keyword_match_rate": result.get("keyword_match_rate", 0),
        "present_keywords":  result.get("present_keywords", []),
        "missing_keywords":  result.get("missing_keywords", []),
        "format_issues":     result.get("format_issues", []),
        "improvements":      result.get("improvements", []),
        "overall_verdict":   result.get("overall_verdict", ""),
        "job_id":            job_id,
    }


# ─────────────────────────────────────────────
# INTERVIEW PREP
# ─────────────────────────────────────────────

@router.post("/interview-prep/{job_id}")
async def interview_prep(job_id: str, user=Depends(get_current_user)):
    """
    Generate interview preparation kit for a specific job.
    Returns likely questions, suggested answers, company research, red flags.
    """
    profile, job = await _get_profile_and_job(user["user_id"], job_id)

    system = (
        "You are a senior career coach preparing a candidate for a job interview. "
        "Based on the job description and candidate's CV, create a comprehensive interview prep kit. "
        "Return ONLY valid JSON: "
        '{"likely_questions": [{"question": "Q", "answer_hint": "how to answer", "difficulty": "easy|medium|hard"}], '
        '"behavioral_questions": [{"question": "Q", "star_example": "situation-action-result hint using their CV"}], '
        '"technical_topics": ["topic1", "topic2"], '
        '"company_research": ["research point 1", "research point 2"], '
        '"questions_to_ask": ["smart question to ask interviewer"], '
        '"red_flags_to_address": ["potential concern and how to handle it"], '
        '"salary_negotiation": "specific advice for this role and market"}'
    )

    user_prompt = (
        f"COMPANY: {job.get('company')}\n"
        f"ROLE: {job.get('title')}\n"
        f"SENIORITY: {job.get('seniority', 'mid')}\n"
        f"LOCATION: {job.get('location')}\n"
        f"JOB DESCRIPTION:\n{job.get('description', '')[:2500]}\n\n"
        f"CANDIDATE CV SUMMARY:\n{profile.get('cv_text', '')[:2000]}\n\n"
        f"CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}"
    )

    try:
        raw = await llm_call(
            task="reasoning",
            system=system,
            user=user_prompt,
            session_id=f"interview_{user['user_id']}_{job_id}",
        )
        result = parse_json_loose(raw)
    except Exception as ex:
        logger.error("interview_prep failed: %s", ex)
        raise HTTPException(500, "Interview prep failed. Please try again.")

    await log_activity(
        user["user_id"], "interview_prep",
        f"Interview prep for {job.get('title')} at {job.get('company')}",
        f"Generated interview preparation kit with {len(result.get('likely_questions', []))} questions.",
        {"job_id": job_id},
    )

    return {
        "likely_questions":     result.get("likely_questions", []),
        "behavioral_questions": result.get("behavioral_questions", []),
        "technical_topics":     result.get("technical_topics", []),
        "company_research":     result.get("company_research", []),
        "questions_to_ask":     result.get("questions_to_ask", []),
        "red_flags_to_address": result.get("red_flags_to_address", []),
        "salary_negotiation":   result.get("salary_negotiation", ""),
        "job_id":  job_id,
        "job_title": job.get("title"),
        "company": job.get("company"),
    }


# ─────────────────────────────────────────────
# SALARY INTELLIGENCE
# ─────────────────────────────────────────────

@router.post("/salary-intel/{job_id}")
async def salary_intelligence(job_id: str, user=Depends(get_current_user)):
    """
    Market salary analysis for a specific role + location combination.
    Uses job data + profile experience to estimate realistic range.
    """
    profile, job = await _get_profile_and_job(user["user_id"], job_id)

    system = (
        "You are a compensation expert with deep knowledge of tech salaries globally. "
        "Provide detailed salary intelligence for this role. "
        "Return ONLY valid JSON: "
        '{"market_range": {"low": 0, "mid": 0, "high": 0, "currency": "EUR"}, '
        '"candidate_range": {"low": 0, "high": 0, "justification": "why this range for them"}, '
        '"negotiation_tips": ["tip1", "tip2"], '
        '"total_comp_factors": ["equity", "bonus", "benefits to negotiate"], '
        '"market_context": "1-2 sentences on market conditions for this role", '
        '"opening_ask": "specific number or range to open negotiation with"}'
    )

    user_prompt = (
        f"ROLE: {job.get('title')}\n"
        f"COMPANY: {job.get('company')}\n"
        f"LOCATION: {job.get('location')}\n"
        f"SENIORITY: {job.get('seniority', 'mid')}\n"
        f"POSTED SALARY: {job.get('salary_range', 'not listed')}\n"
        f"SKILLS REQUIRED: {', '.join(job.get('skills_required', []))}\n\n"
        f"CANDIDATE YEARS EXPERIENCE: {profile.get('years_experience', 'unknown')}\n"
        f"CANDIDATE SKILLS: {', '.join(profile.get('skills', []))[:500]}\n"
        f"CANDIDATE LOCATION: {profile.get('location', 'unknown')}"
    )

    try:
        raw = await llm_call(
            task="fast",
            system=system,
            user=user_prompt,
            session_id=f"salary_{user['user_id']}_{job_id}",
        )
        result = parse_json_loose(raw)
    except Exception as ex:
        logger.error("salary_intel failed: %s", ex)
        raise HTTPException(500, "Salary analysis failed. Please try again.")

    return {
        "market_range":        result.get("market_range", {}),
        "candidate_range":     result.get("candidate_range", {}),
        "negotiation_tips":    result.get("negotiation_tips", []),
        "total_comp_factors":  result.get("total_comp_factors", []),
        "market_context":      result.get("market_context", ""),
        "opening_ask":         result.get("opening_ask", ""),
        "job_id":              job_id,
        "posted_salary":       job.get("salary_range"),
    }
