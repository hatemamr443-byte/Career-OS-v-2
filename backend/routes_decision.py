"""
AI Decision Engine — Career Intelligence Core.

Migrated in P1 Brain Activation: every LLM call now flows through
`orchestrator.run()` so the Decision Engine inherits:
  - unified persona / voice
  - scored career memory injection
  - career context injection
  - per-call telemetry
  - event publication into the bus

Endpoints (unchanged response shapes for backward compatibility):
  POST /api/decision/match/{job_id}      — enhanced job match w/ strategic fields
  POST /api/decision/career-roi          — compare 2-3 opportunities by ROI
  GET  /api/decision/strategic-plan      — personalized 90-day plan
  GET  /api/decision/wellbeing-check     — heuristic-only burnout indicator
  GET  /api/decision/skill-gaps          — skill gap analysis
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import profiles, jobs, applications, db as mongo_db
from models import new_id
from auth import get_current_user
from career_intelligence import CareerIntelligence
from orchestrator import orchestrator
from ai_limits import check_ai_quota
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/decision", tags=["decision-engine"])


# ─────────────────────────────────────────────
# ENHANCED JOB MATCH (with strategic reasoning)
# ─────────────────────────────────────────────

@router.post("/match/{job_id}")
async def enhanced_job_match(job_id: str, user=Depends(get_current_user)):
    """Full AI match analysis via orchestrator (memory + context + telemetry)."""
    await check_ai_quota(user, "ai_match")

    job = await jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")

    # Cross-feature signals for prompt enrichment
    ci = CareerIntelligence(user["user_id"])
    signals = await ci.cross_feature_signals()
    rejected_patterns = ", ".join(signals.get("skill_gaps_from_rejections", [])[:5])
    salary_context = signals.get("salary_market_context", {})

    feature_prompt = (
        "You are performing a strategic match analysis for this user. "
        "Anchor every judgement in the user's career memory and history above. "
        "Return ONLY valid JSON in this exact schema:\n"
        '{"score": 0-100, '
        '"confidence": 0-100, '
        '"decision": "apply|consider|skip", '
        '"reasoning": "2-3 sentence strategic rationale", '
        '"strengths": ["specific strength"], '
        '"gaps": ["specific gap to address"], '
        '"matching_skills": ["skill present in both"], '
        '"missing_skills": ["required but missing"], '
        '"salary_fit": "above_range|within_range|below_range|unknown", '
        '"location_fit": "matches|relocatable|remote|mismatch", '
        '"growth_potential": "high|medium|low", '
        # ── New strategic fields (P1) ────────────────────────────
        '"trajectory_impact": "how this role bends their 5-yr career arc — one sentence", '
        '"compensation_growth_outlook": "↑ strong | → stable | ↓ limited — w/ one-line why", '
        '"skill_compounding": ["skills here that compound with what they already have"], '
        '"risk_flags": ["specific risk: e.g. seniority mismatch, comp band, culture signal"], '
        # ── Existing fields preserved ────────────────────────────
        '"strategic_advice": "one sentence on how to approach this", '
        '"expected_outcome": "realistic outcome if applied", '
        '"cv_tailoring_priority": ["top 3 things to emphasize in CV"]}'
    )

    user_message = (
        f"JOB:\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Location: {job['location']}\nRemote: {job.get('remote', False)}\n"
        f"Salary: {job.get('salary_range', 'not listed')}\n"
        f"Description:\n{job.get('description', '')[:2500]}\n\n"
        f"ADDITIONAL SIGNALS:\n"
        f"Candidate's common skill gaps from rejected jobs: {rejected_patterns or 'none identified'}\n"
        f"Market salary for similar roles: {salary_context.get('market_median', 'unknown')}\n"
    )

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="decision_match",
            task="reasoning",
            feature_prompt=feature_prompt,
            user_message=user_message,
            session_id=f"match_{user['user_id']}_{job_id}",
            memory_k=6,
            context_depth="standard",
            publish_event="match_analyzed",
            event_payload={
                "job_id": job_id,
                "company": job.get("company"),
                "title": job.get("title"),
            },
        )
        result = orchestrator.parse_json(text)

        # Cache result
        await mongo_db.decisions.update_one(
            {"user_id": user["user_id"], "job_id": job_id},
            {"$set": {
                "result":     result,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

        return {**result, "job_id": job_id, "analyzed_at": datetime.now(timezone.utc).isoformat()}

    except Exception as ex:
        logger.error("enhanced_match failed job=%s: %s", job_id, ex)
        raise HTTPException(500, "Match analysis failed.")


# ─────────────────────────────────────────────
# CAREER ROI ANALYSIS
# ─────────────────────────────────────────────

@router.post("/career-roi")
async def career_roi_analysis(payload: dict, user=Depends(get_current_user)):
    """Compare 2-3 opportunities by career ROI (via orchestrator)."""
    await check_ai_quota(user, "ai_match")
    job_ids = payload.get("job_ids", [])
    if not job_ids or len(job_ids) < 2:
        raise HTTPException(400, "Provide at least 2 job_ids to compare.")

    job_docs = await jobs.find(
        {"job_id": {"$in": job_ids[:3]}}, {"_id": 0}
    ).to_list(3)

    if not job_docs:
        raise HTTPException(404, "Jobs not found.")

    jobs_text = "\n\n".join([
        f"Job {i+1}: {j['title']} at {j['company']}\n"
        f"Salary: {j.get('salary_range', 'not listed')}\n"
        f"Skills: {', '.join(j.get('skills_required', []))}"
        for i, j in enumerate(job_docs)
    ])

    feature_prompt = (
        "You are performing ROI analysis on these job opportunities. "
        "Consider: salary growth, skill acquisition, company prestige, network access, "
        "work-life balance signals, exit opportunities, 3-year career impact. "
        "Anchor your judgement in the user's history and memory above. "
        "Return ONLY valid JSON:\n"
        '{"jobs": [{'
        '"job_index": 1,'
        '"title": "job title",'
        '"company": "company",'
        '"roi_score": 0-100,'
        '"salary_trajectory": "↑ strong growth | → stable | ↓ limited",'
        '"skill_growth": ["skills you will gain"],'
        '"network_value": "high|medium|low",'
        '"exit_opportunities": "description",'
        '"career_capital": "what this adds to your career story",'
        '"risks": ["risk"],'
        '"verdict": "one sentence verdict"'
        '}], '
        '"winner": "Job 1|2|3",'
        '"strategic_recommendation": "2-3 sentence final advice"}'
    )

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="decision_career_roi",
            task="reasoning",
            feature_prompt=feature_prompt,
            user_message=f"Compare these opportunities:\n\n{jobs_text}",
            session_id=f"roi_{user['user_id']}_{new_id('roi')}",
            memory_k=8,
            context_depth="full",
            publish_event="career_roi_analyzed",
            event_payload={"job_ids": job_ids[:3]},
        )
        return orchestrator.parse_json(text)
    except Exception as ex:
        logger.error("career_roi failed: %s", ex)
        raise HTTPException(500, "ROI analysis failed.")


# ─────────────────────────────────────────────
# STRATEGIC CAREER PLANNER
# ─────────────────────────────────────────────

@router.get("/strategic-plan")
async def strategic_career_plan(user=Depends(get_current_user)):
    """Generate a personalized 90-day strategic career plan (via orchestrator)."""
    await check_ai_quota(user, "ai_match")
    ci = CareerIntelligence(user["user_id"])
    signals = await ci.cross_feature_signals()

    feature_prompt = (
        "Create a concrete, actionable 90-day plan. Be specific — no generic advice. "
        "Tailor everything to this person's exact situation drawn from memory + context. "
        "Return ONLY valid JSON:\n"
        '{"situation_assessment": "honest 2-sentence assessment", '
        '"biggest_blocker": "the #1 thing slowing them down", '
        '"week_1_4": ["specific action"], '
        '"week_5_8": ["specific action"], '
        '"week_9_12": ["specific action"], '
        '"skill_priorities": ["skill to learn with reason"], '
        '"application_strategy": "targeted advice on how to apply", '
        '"salary_strategy": "salary negotiation approach", '
        '"network_moves": ["specific networking action"], '
        '"success_metrics": ["how to measure progress"], '
        '"warning_signs": ["red flag to watch for"]}'
    )

    user_message = (
        f"Cross-feature signals:\n"
        f"Skill gaps: {signals.get('skill_gaps_from_rejections', [])}\n"
        f"High-interest companies: {signals.get('high_interest_companies', [])}\n"
        "Generate a personalized 90-day career strategy."
    )

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="decision_strategic_plan",
            task="reasoning",
            feature_prompt=feature_prompt,
            user_message=user_message,
            session_id=f"plan_{user['user_id']}_{new_id('plan')}",
            memory_k=10,
            context_depth="full",
            publish_event="decision_strategic_plan",
            event_payload={"requested_at": datetime.now(timezone.utc).isoformat()},
        )
        result = orchestrator.parse_json(text)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as ex:
        logger.error("strategic_plan failed: %s", ex)
        raise HTTPException(500, "Strategic plan generation failed.")


# ─────────────────────────────────────────────
# BURNOUT RISK INDICATOR (heuristic — no LLM)
# ─────────────────────────────────────────────

@router.get("/wellbeing-check")
async def wellbeing_check(user=Depends(get_current_user)):
    """Heuristic burnout indicator. No LLM (intentional — privacy + speed)."""
    uid = user["user_id"]

    recent_apps = await applications.find(
        {"user_id": uid}, {"_id": 0, "status": 1, "created_at": 1}
    ).sort("created_at", -1).limit(30).to_list(30)

    rejection_streak = 0
    for app in recent_apps:
        if app.get("status") == "rejected":
            rejection_streak += 1
        else:
            break

    total_apps = len(recent_apps)
    offer_count = sum(1 for a in recent_apps if a.get("status") == "offer")

    user_doc = await mongo_db.users.find_one({"user_id": uid}, {"_id": 0}) or {}
    streak = user_doc.get("streak", 0)

    risk_score = 0
    if rejection_streak >= 5:  risk_score += 30
    if rejection_streak >= 10: risk_score += 20
    if total_apps > 50 and offer_count == 0: risk_score += 25
    if streak == 0: risk_score += 10
    risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"

    recommendations = []
    if rejection_streak >= 5:
        recommendations.append("Take a 2-day break from applying — refresh your CV strategy first")
    if total_apps > 30 and offer_count == 0:
        recommendations.append("Narrow your target: focus on 5 specific companies rather than broad applications")
    if risk_level == "high":
        recommendations.append("Consider speaking with a career coach or mentor")
    if streak < 3:
        recommendations.append("Small daily wins build momentum — even 15 minutes of career work counts")
    if not recommendations:
        recommendations.append("You're doing well — keep the momentum going")

    return {
        "risk_level":       risk_level,
        "risk_score":       risk_score,
        "rejection_streak": rejection_streak,
        "total_applications": total_apps,
        "offers_received":  offer_count,
        "current_streak":   streak,
        "recommendations":  recommendations,
        "message": (
            "Your job search is progressing well." if risk_level == "low"
            else "Some patterns suggest you might benefit from a strategy reset."
            if risk_level == "medium"
            else "Consider pausing applications briefly to refresh your approach."
        ),
    }


# ─────────────────────────────────────────────
# SKILL GAP ANALYSIS
# ─────────────────────────────────────────────

@router.get("/skill-gaps")
async def skill_gap_analysis(user=Depends(get_current_user)):
    """Analyze skill gaps via orchestrator (memory + context)."""
    await check_ai_quota(user, "ai_match")
    ci = CareerIntelligence(user["user_id"])
    signals = await ci.cross_feature_signals()

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    my_skills = profile.get("skills", [])

    apps = await applications.find(
        {"user_id": user["user_id"]}, {"_id": 0, "job_id": 1}
    ).limit(30).to_list(30)

    market_skills: dict[str, int] = {}
    if apps:
        job_ids = [a["job_id"] for a in apps]
        async for j in jobs.find(
            {"job_id": {"$in": job_ids}}, {"_id": 0, "skills_required": 1}
        ):
            for s in j.get("skills_required", []):
                market_skills[s] = market_skills.get(s, 0) + 1

    top_market_skills = sorted(market_skills.items(), key=lambda x: -x[1])[:15]
    gaps = [s for s, _ in top_market_skills if s not in set(my_skills)]

    feature_prompt = (
        "Analyze skill gaps and provide a learning roadmap. "
        "Return ONLY valid JSON:\n"
        '{"critical_gaps": ["skill|reason|time_to_learn"],'
        '"quick_wins": ["skill learnable in < 2 weeks"],'
        '"long_term_skills": ["skill requiring months"],'
        '"learning_resources": [{"skill":"","resource":"","free":true}],'
        '"priority_order": ["ordered list of what to learn first"],'
        '"impact_estimate": "how closing these gaps affects interview rate"}'
    )

    user_message = (
        f"My current skills: {', '.join(my_skills[:20])}\n"
        f"Skills appearing in target jobs: {', '.join(gaps[:15])}\n"
        f"Gaps identified from rejections: {', '.join(signals.get('skill_gaps_from_rejections', []))}\n"
        f"Target roles: {', '.join(profile.get('target_roles', []))}"
    )

    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="decision_skill_gaps",
            task="fast",
            feature_prompt=feature_prompt,
            user_message=user_message,
            session_id=f"skills_{user['user_id']}_{new_id('sk')}",
            memory_k=5,
            context_depth="standard",
            publish_event="skill_gap_analyzed",
            event_payload={"gaps": gaps[:10]},
        )
        result = orchestrator.parse_json(text)
        result["raw_gaps"]   = gaps[:10]
        result["my_skills"]  = my_skills
        return result
    except Exception as ex:
        logger.error("skill_gap failed: %s", ex)
        return {"raw_gaps": gaps[:10], "my_skills": my_skills, "error": "AI analysis unavailable"}
