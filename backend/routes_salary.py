"""Salary Intelligence: market rates, offer evaluation, negotiation scripts.
All AI calls route through orchestrator.run() for unified persona + memory + telemetry.
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import profiles, jobs
from models import new_id
from auth import get_current_user
from llm_schemas import parse_llm_json
from orchestrator import orchestrator
from ai_limits import check_ai_quota
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/salary", tags=["salary"])

SALARY_JSON_SCHEMA = (
    '{"currency": "EUR|USD|GBP", '
    '"annual_min": 0, "annual_max": 0, "annual_median": 0, '
    '"monthly_min": 0, "monthly_max": 0, '
    '"hourly_min": 0, "hourly_max": 0, '
    '"confidence": "high|medium|low", '
    '"factors": ["factor"], '
    '"notes": "context", '
    '"data_sources": ["Glassdoor"], '
    '"comparison": {"junior": 0, "mid": 0, "senior": 0}}'
)


@router.post("/range")
async def salary_range(payload: dict, user=Depends(get_current_user)):
    """Get salary range estimate for a role + location + experience."""
    role       = payload.get("role", "")
    location   = payload.get("location", "")
    experience = payload.get("years_experience", 0)
    job_id     = payload.get("job_id")

    if job_id and not role:
        job      = await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}
        role     = job.get("title", "")
        location = location or job.get("location", "")

    if not role:
        profile    = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
        role       = payload.get("role") or ", ".join(profile.get("target_roles", []))[:50]
        location   = location or (profile.get("target_locations") or [""])[0]
        experience = experience or profile.get("years_experience", 0)

    if not role:
        raise HTTPException(400, "Provide role or job_id.")

    await check_ai_quota(user, "salary_range")
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="salary_range",
            task="fast",
            feature_prompt=(
                "You are a compensation expert with global salary data. "
                "Use the user's career context to personalise estimates.\n"
                "Return ONLY valid JSON:\n" + SALARY_JSON_SCHEMA
            ),
            user_message=(
                f"Role: {role}\nLocation: {location or 'not specified'}\n"
                f"Years of experience: {experience}\n"
                "Provide estimates in local currency for the location."
            ),
            session_id=f"sal_{user['user_id']}_{hash(role + location) % 99999}",
            publish_event="salary_research",
            event_payload={"role": role, "location": location},
        )
        result = parse_llm_json(text)
        result.update({"role": role, "location": location,
                        "experience": experience,
                        "queried_at": datetime.now(timezone.utc).isoformat()})
        return result
    except Exception as ex:
        logger.error("salary_range failed: %s", ex)
        raise HTTPException(500, "Salary estimate failed.")


@router.post("/evaluate-offer")
async def evaluate_offer(payload: dict, user=Depends(get_current_user)):
    """Evaluate if a job offer is fair given market rates."""
    offered_salary = payload.get("offered_salary", 0)
    currency       = payload.get("currency", "EUR")
    role           = payload.get("role", "")
    location       = payload.get("location", "")
    benefits       = payload.get("benefits", [])
    job_id         = payload.get("job_id")

    if job_id and not role:
        job      = await jobs.find_one({"job_id": job_id}, {"_id": 0}) or {}
        role     = job.get("title", "")
        location = location or job.get("location", "")

    profile    = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    experience = profile.get("years_experience", 0)

    await check_ai_quota(user, "evaluate_offer")
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="salary_evaluate_offer",
            task="fast",
            feature_prompt=(
                "You are a compensation expert evaluating a job offer. "
                "Factor in this user's experience and career trajectory. Be direct.\n"
                'Return ONLY valid JSON:\n{"verdict": "below_market|at_market|above_market", '
                '"verdict_label": "Below Market|Fair|Strong Offer", "percent_vs_market": -20, '
                '"market_range": {"min": 0, "max": 0, "median": 0}, "total_compensation": 0, '
                '"benefits_value": "low|fair|strong", "recommendation": "accept|negotiate|decline", '
                '"negotiation_room": "0-20%", "key_points": ["insight"], "bottom_line": "verdict"}'
            ),
            user_message=(
                f"Offered salary: {offered_salary} {currency}/year\nRole: {role}\n"
                f"Location: {location}\nYears experience: {experience}\n"
                f"Benefits: {', '.join(benefits) if benefits else 'not specified'}"
            ),
            session_id=f"ofr_{user['user_id']}_{new_id('ofr')}",
        )
        result = parse_llm_json(text)
        result.update({"offered_salary": offered_salary, "currency": currency})
        return result
    except Exception as ex:
        logger.error("evaluate_offer failed: %s", ex)
        raise HTTPException(500, "Offer evaluation failed.")


@router.post("/negotiate")
async def negotiation_script(payload: dict, user=Depends(get_current_user)):
    """Generate a salary negotiation email/script."""
    current_offer = payload.get("current_offer", 0)
    target_salary = payload.get("target_salary", 0)
    currency      = payload.get("currency", "EUR")
    role          = payload.get("role", "")
    company       = payload.get("company", "")
    reason        = payload.get("reason", "market research")
    tone          = payload.get("tone", "professional")

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    name    = profile.get("full_name", "")

    await check_ai_quota(user, "negotiate")
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="salary_negotiate",
            task="reasoning",
            feature_prompt=(
                "You are a salary negotiation coach writing for this specific user. "
                "Leverage their career history and skills in the negotiation.\n"
                'Return ONLY valid JSON:\n{"email_subject": "...", "email_body": "...", '
                '"key_points": ["point"], "talking_points": ["point"], '
                '"what_not_to_say": ["mistake"], "backup_asks": ["ask"], '
                '"success_probability": "low|medium|high", "tips": ["tip"]}'
            ),
            user_message=(
                f"Candidate: {name}\nRole: {role} at {company}\n"
                f"Current offer: {current_offer} {currency}\n"
                f"Target: {target_salary} {currency}\n"
                f"Reason: {reason}\nTone: {tone}"
            ),
            session_id=f"neg_{user['user_id']}_{new_id('neg')}",
        )
        result = parse_llm_json(text)
        result.update({"current_offer": current_offer, "target_salary": target_salary})
        return result
    except Exception as ex:
        logger.error("negotiation_script failed: %s", ex)
        raise HTTPException(500, "Negotiation script generation failed.")


@router.get("/cost-of-living")
async def cost_of_living_comparison(
    from_city: str,
    to_city: str,
    current_salary: float,
    user=Depends(get_current_user),
):
    """Compare cost of living between two cities and suggest salary adjustment."""
    await check_ai_quota(user, "cost_of_living")
    try:
        text = await orchestrator.run(
            user_id=user["user_id"],
            feature="salary_col",
            task="fast",
            feature_prompt=(
                "You are a relocation compensation expert.\n"
                'Return ONLY valid JSON:\n{"cost_index_from": 100, "cost_index_to": 100, '
                '"adjustment_factor": 1.2, "equivalent_salary_to": 0, '
                '"breakdown": {"housing": "+20%", "food": "-5%", "transport": "+10%", "healthcare": "0%"}, '
                '"verdict": "higher|lower|similar cost", "recommendation": "advice", '
                '"key_differences": ["difference"]}'
            ),
            user_message=(
                f"Moving from: {from_city}\nMoving to: {to_city}\n"
                f"Current salary: {current_salary}"
            ),
            session_id=f"col_{user['user_id']}_{hash(from_city + to_city) % 99999}",
        )
        result = parse_llm_json(text)
        result.update({"from_city": from_city, "to_city": to_city,
                        "current_salary": current_salary})
        return result
    except Exception as ex:
        logger.error("cost_of_living failed: %s", ex)
        raise HTTPException(500, "Cost of living comparison failed.")
