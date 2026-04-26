"""Insights / analytics."""
from fastapi import APIRouter, Depends
from db import applications, jobs as jobs_col
from auth import get_current_user

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
async def insights(user=Depends(get_current_user)):
    apps = await applications.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(500)
    total = len(apps)
    by_status = {"discovered": 0, "applied": 0, "under_review": 0, "interview": 0, "offer": 0, "rejected": 0}
    for a in apps:
        s = a.get("status", "discovered")
        by_status[s] = by_status.get(s, 0) + 1

    applied = by_status["applied"] + by_status["under_review"] + by_status["interview"] + by_status["offer"] + by_status["rejected"]
    interview_rate = round(100 * (by_status["interview"] + by_status["offer"]) / applied, 1) if applied else 0
    rejection_rate = round(100 * by_status["rejected"] / applied, 1) if applied else 0
    success_rate = round(100 * by_status["offer"] / applied, 1) if applied else 0

    # Funnel
    funnel = [
        {"stage": "Applied", "count": applied},
        {"stage": "Under Review", "count": by_status["under_review"] + by_status["interview"] + by_status["offer"]},
        {"stage": "Interview", "count": by_status["interview"] + by_status["offer"]},
        {"stage": "Offer", "count": by_status["offer"]},
    ]

    # Rejection patterns by company seniority
    rej_apps = [a for a in apps if a.get("status") == "rejected"]
    rejection_pattern = {"junior": 0, "mid": 0, "senior": 0, "lead": 0}
    if rej_apps:
        job_ids = [a["job_id"] for a in rej_apps]
        async for j in jobs_col.find({"job_id": {"$in": job_ids}}, {"_id": 0}):
            sen = j.get("seniority", "mid")
            rejection_pattern[sen] = rejection_pattern.get(sen, 0) + 1

    return {
        "totals": {"total": total, **by_status},
        "rates": {
            "interview_rate": interview_rate,
            "rejection_rate": rejection_rate,
            "success_rate": success_rate,
        },
        "funnel": funnel,
        "rejection_pattern_by_seniority": rejection_pattern,
    }
