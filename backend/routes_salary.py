"""Salary Intelligence: market rates, offer evaluation, negotiation scripts."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from db import profiles, jobs
from models import new_id
from auth import get_current_user
from llm_service import llm_call, parse_json_loose
from ai_limits import check_ai_quota
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/salary", tags=["salary"])


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
        profile  = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
        role     = payload.get("role") or ", ".join(profile.get("target_roles", []))[:50]
        location = location or profile.get("target_locations", [""])[0]
        experience = experience or profile.get("years_experience", 0)

    if not role:
        raise HTTPException(400, "Provide role or job_id.")

    await check_ai_quota(user, "salary_range")

    try:
        text = await llm_call(
            task="fast",
            system=(
                "You are a compensation expert with knowledge of global salary data. "
                "Provide realistic salary estimates based on role, location, and experience. "
                "Be specific and honest about uncertainty in estimates. "
                "Return ONLY valid JSON:\n"
                '{"currency": "EUR|USD|GBP", '
                '"annual_min": 0, "annual_max": 0, "annual_median": 0, '
                '"monthly_min": 0, "monthly_max": 0, '
                '"hourly_min": 0, "hourly_max": 0, '
                '"confidence": "high|medium|low", '
                '"factors": ["factor affecting salary"], '
                '"notes": "important context", '
                '"data_sources": ["Glassdoor", "LinkedIn Salary", "etc"], '
                '"comparison": {"junior": 0, "mid": 0, "senior": 0}}'
            ),
            user=(
                f"Role: {role}\n"
                f"Location: {location or 'not specified'}\n"
                f"Years of experience: {experience}\n"
                f"Note: provide estimates in local currency for the location."
            ),
            session_id=f"sal_{user['user_id']}_{hash(role+location) % 99999}",
        )
        result = parse_json_loose(text)
        result["role"]       = role
        result["location"]   = location
        result["experience"] = experience
        result["queried_at"] = datetime.now(timezone.utc).isoformat()
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
        text = await llm_call(
            task="fast",
            system=(
                "You are a compensation expert evaluating a job offer. "
                "Be direct and honest. "
                "Return ONLY valid JSON:\n"
                '{"verdict": "below_market|at_market|above_market", '
                '"verdict_label": "Below Market|Fair|Strong Offer", '
                '"percent_vs_market": -20 or 5 etc, '
                '"market_range": {"min": 0, "max": 0, "median": 0}, '
                '"total_compensation": 0, '
                '"benefits_value": "low|fair|strong", '
                '"recommendation": "accept|negotiate|decline", '
                '"negotiation_room": "0-20%", '
                '"key_points": ["insight about this offer"], '
                '"bottom_line": "one sentence verdict"}'
            ),
            user=(
                f"Offered salary: {offered_salary} {currency}/year\n"
                f"Role: {role}\n"
                f"Location: {location}\n"
                f"Years of experience: {experience}\n"
                f"Benefits offered: {', '.join(benefits) if benefits else 'not specified'}"
            ),
            session_id=f"ofr_{user['user_id']}_{new_id('ofr')}",
        )
        result = parse_json_loose(text)
        result["offered_salary"] = offered_salary
        result["currency"]       = currency
        return result

    except Exception as ex:
        logger.error("evaluate_offer failed: %s", ex)
        raise HTTPException(500, "Offer evaluation failed.")


@router.post("/negotiate")
async def negotiation_script(payload: dict, user=Depends(get_current_user)):
    """Generate a salary negotiation email/script."""
    current_offer  = payload.get("current_offer", 0)
    target_salary  = payload.get("target_salary", 0)
    currency       = payload.get("currency", "EUR")
    role           = payload.get("role", "")
    company        = payload.get("company", "")
    reason         = payload.get("reason", "market research")  # competing offer, market research, etc.
    tone           = payload.get("tone", "professional")       # professional | confident | flexible

    profile = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    name    = profile.get("full_name", "")

    await check_ai_quota(user, "negotiate")

    try:
        text = await llm_call(
            task="reasoning",
            system=(
                "You are an expert salary negotiation coach. "
                "Write a professional negotiation email that is confident but not aggressive. "
                "Return ONLY valid JSON:\n"
                '{"email_subject": "subject line", '
                '"email_body": "full email text", '
                '"key_points": ["negotiation point"], '
                '"talking_points": ["point to mention in call"], '
                '"what_not_to_say": ["mistake to avoid"], '
                '"backup_asks": ["if salary fails, ask for this"], '
                '"success_probability": "low|medium|high", '
                '"tips": ["negotiation tip"]}'
            ),
            user=(
                f"Candidate: {name}\n"
                f"Role: {role} at {company}\n"
                f"Current offer: {current_offer} {currency}\n"
                f"Target salary: {target_salary} {currency}\n"
                f"Reason for negotiating: {reason}\n"
                f"Tone: {tone}"
            ),
            session_id=f"neg_{user['user_id']}_{new_id('neg')}",
        )
        result = parse_json_loose(text)
        result["current_offer"] = current_offer
        result["target_salary"] = target_salary
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
    """Compare cost of living between two cities and adjust salary."""
    await check_ai_quota(user, "cost_of_living")
    try:
        text = await llm_call(
            task="fast",
            system=(
                "You are a relocation compensation expert. "
                "Compare cost of living and suggest salary adjustment. "
                "Return ONLY valid JSON:\n"
                '{"cost_index_from": 100, "cost_index_to": 100, '
                '"adjustment_factor": 1.2, '
                '"equivalent_salary_to": 0, '
                '"breakdown": {"housing": "+20%", "food": "-5%", "transport": "+10%", "healthcare": "0%"}, '
                '"verdict": "higher|lower|similar cost", '
                '"recommendation": "advice on relocation from salary perspective", '
                '"key_differences": ["key difference between cities"]}'
            ),
            user=(
                f"Moving from: {from_city}\n"
                f"Moving to: {to_city}\n"
                f"Current salary: {current_salary}\n"
                "Provide realistic estimates."
            ),
            session_id=f"col_{user['user_id']}_{hash(from_city+to_city) % 99999}",
        )
        result = parse_json_loose(text)
        result["from_city"]       = from_city
        result["to_city"]         = to_city
        result["current_salary"]  = current_salary
        return result

    except Exception as ex:
        logger.error("cost_of_living failed: %s", ex)
        raise HTTPException(500, "Cost of living comparison failed.")
