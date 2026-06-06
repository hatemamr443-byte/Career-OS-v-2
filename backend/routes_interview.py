"""Interview Intelligence: question generation, answer evaluation, company research.
All AI calls route through orchestrator.run() for unified persona + memory + telemetry.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from db import profiles, jobs, interview_sessions
from models import new_id
from auth import get_current_user
from llm_schemas import parse_llm_json
from orchestrator import orchestrator
from event_bus import event_bus
from activity import log_activity
from ai_limits import check_ai_quota
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interview", tags=["interview"])


# ─────────────────────────────────────────────
# GENERATE QUESTIONS
# ─────────────────────────────────────────────

@router.post("/questions")
async def generate_questions(payload: dict, user=Depends(get_current_user)):
    """Generate likely interview questions for a specific job."""
    job_id  = payload.get("job_id")
    count   = min(payload.get("count", 10), 20)
    types   = payload.get("types", ["behavioral", "technical", "situational"])

    profile  = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    cv_text  = profile.get("cv_text", "")

    job = {}
    if job_id:
        job = await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}

    job_title   = job.get("title")       or payload.get("job_title", "")
    job_company = job.get("company")     or payload.get("company", "")
    job_text    = job.get("description") or payload.get("job_description", "")

    if not job_title and not job_text:
        raise HTTPException(400, "Provide job_id or job_title + job_description.")

    await check_ai_quota(user, "interview_questions")

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="interview_questions",
            task="reasoning",
            feature_prompt=(
                "You are an expert interview coach with deep knowledge of hiring practices. "
                "You have the user's full career history — use it to make questions hyper-relevant. "
                "Generate realistic interview questions based on the job and candidate's background.\n"
                "Return ONLY valid JSON:\n"
                '{"questions": [{'
                '"id": "q1", '
                '"question": "the question", '
                '"type": "behavioral|technical|situational|culture_fit|role_specific", '
                '"difficulty": "easy|medium|hard", '
                '"why_asked": "brief reason", '
                '"tips": "brief tip for answering"'
                '}], '
                '"focus_areas": ["area to prepare"], '
                '"red_flags": ["potential concern from your background"]}'
            ),
            user_message=(
                f"ROLE: {job_title} at {job_company}\n"
                f"JOB DESCRIPTION:\n{job_text[:2500]}\n\n"
                f"CANDIDATE CV:\n{cv_text[:1500]}\n\n"
                f"Generate exactly {count} questions. "
                f"Types requested: {', '.join(types)}."
            ),
            session_id=f"iq_{user['user_id']}_{new_id('iq')}",
            publish_event="interview_prep_started",
            event_payload={"job_id": job_id, "job_title": job_title, "company": job_company},
        )
        result = parse_llm_json(text)

        session_id = new_id("ivs")
        await interview_sessions.insert_one({
            "session_id":   session_id,
            "user_id":      user["user_id"],
            "job_id":       job_id,
            "job_title":    job_title,
            "job_company":  job_company,
            "questions":    result.get("questions", []),
            "answers":      {},
            "evaluations":  {},
            "created_at":   datetime.now(timezone.utc).isoformat(),
        })

        await log_activity(
            user["user_id"], "interview_prep",
            f"Interview prep for {job_title}",
            f"Generated {len(result.get('questions', []))} interview questions for {job_company}",
            {"job_id": job_id, "session_id": session_id},
        )

        result["session_id"] = session_id
        return result

    except Exception as ex:
        logger.error("generate_questions failed: %s", ex)
        raise HTTPException(500, "Question generation failed.")


# ─────────────────────────────────────────────
# EVALUATE ANSWER
# ─────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_answer(payload: dict, user=Depends(get_current_user)):
    """Evaluate a candidate's answer to an interview question."""
    question   = payload.get("question", "")
    answer     = payload.get("answer", "")
    session_id = payload.get("session_id")
    q_id       = payload.get("question_id", "")

    if not question or not answer:
        raise HTTPException(400, "Both question and answer are required.")

    await check_ai_quota(user, "interview_evaluate")

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    cv_text = profile.get("cv_text", "")

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="interview_evaluate",
            task="fast",
            feature_prompt=(
                "You are a senior hiring manager evaluating a candidate's interview answer. "
                "You know this candidate's background — hold them to the right standard for "
                "their experience level. Be honest, specific, and constructive.\n"
                "Return ONLY valid JSON:\n"
                '{"score": 0-10, '
                '"verdict": "strong|acceptable|weak", '
                '"strengths": ["what was good"], '
                '"improvements": ["specific improvement"], '
                '"better_answer": "an improved version of their answer", '
                '"star_used": true|false, '
                '"feedback": "2-3 sentence honest feedback"}'
            ),
            user_message=(
                f"QUESTION: {question}\n\n"
                f"CANDIDATE ANSWER: {answer}\n\n"
                f"CANDIDATE BACKGROUND:\n{cv_text[:1000]}"
            ),
            session_id=f"eval_{user['user_id']}_{new_id('ev')}",
            publish_event="interview_answer_evaluated",
            event_payload={"session_id": session_id, "q_id": q_id},
        )
        result = parse_llm_json(text)

        if session_id:
            await interview_sessions.update_one(
                {"session_id": session_id, "user_id": user["user_id"]},
                {"$set": {
                    f"answers.{q_id}":     answer,
                    f"evaluations.{q_id}": result,
                }},
            )

        return result

    except Exception as ex:
        logger.error("evaluate_answer failed: %s", ex)
        raise HTTPException(500, "Answer evaluation failed.")


# ─────────────────────────────────────────────
# COMPANY RESEARCH
# ─────────────────────────────────────────────

@router.get("/company-research")
async def company_research(
    company: str = Query(..., min_length=1),
    role: str    = Query("", min_length=0),
    user=Depends(get_current_user),
):
    """AI-generated company research summary for interview prep."""
    await check_ai_quota(user, "company_research")
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="interview_research",
            task="fast",
            feature_prompt=(
                "You are a career research analyst preparing a candidate for an interview. "
                "You know this user's career history — tailor the research to what matters for them.\n"
                "Return ONLY valid JSON:\n"
                '{"company_overview": "2-3 sentences", '
                '"culture_notes": ["culture insight"], '
                '"typical_interview_process": ["step"], '
                '"common_interview_questions": ["question"], '
                '"things_to_mention": ["talking point that impresses"], '
                '"red_flags": ["potential concern"], '
                '"glassdoor_themes": ["common employee theme"], '
                '"prep_tips": ["specific tip for this company"]}'
            ),
            user_message=f"Company: {company}\nRole being applied for: {role or 'not specified'}",
            session_id=f"cmp_{user['user_id']}_{hash(company) % 99999}",
            publish_event="company_researched",
            event_payload={"company": company, "role": role},
        )
        result = parse_llm_json(text)
        result["company"] = company
        result["role"]    = role
        return result

    except Exception as ex:
        logger.error("company_research failed: %s", ex)
        raise HTTPException(500, "Company research failed.")


# ─────────────────────────────────────────────
# SESSION HISTORY
# ─────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user), limit: int = 10):
    docs = await interview_sessions.find(
        {"user_id": user["user_id"]}, {"_id": 0, "questions": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"sessions": docs, "count": len(docs)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user)):
    doc = await interview_sessions.find_one(
        {"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Session not found.")
    return doc


@router.post("/sessions/{session_id}/complete")
async def complete_session(session_id: str, payload: dict, user=Depends(get_current_user)):
    """Mark interview session as complete — fires interview_completed event for orchestrator."""
    doc = await interview_sessions.find_one(
        {"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Session not found.")

    await interview_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "outcome":      payload.get("outcome", "completed"),
        }},
    )

    # Fire event so orchestrator can update career graph + surface insights
    await event_bus.publish(
        "interview_completed",
        user["user_id"],
        {
            "session_id":  session_id,
            "job_id":      doc.get("job_id"),
            "job_title":   doc.get("job_title"),
            "job_company": doc.get("job_company"),
            "outcome":     payload.get("outcome", "completed"),
        },
    )

    return {"ok": True, "session_id": session_id}
