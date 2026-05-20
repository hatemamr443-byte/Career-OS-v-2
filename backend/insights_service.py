"""
Career OS — Insights Synthesizer.

Surfaces the orchestration layer's outputs to the user as a small set of
unified, typed Insight cards.

Design principles (from approved spec):
  - calm, strategic guidance — not AI overload
  - one consistent voice across all insights
  - source signals + confidence + dismissible (transparency)
  - passive intelligence (no AI calls here — pure aggregation)
  - bounded count (max ~5 cards) — prevents noise

This is intentionally a synthesizer over the orchestration outputs that
already exist in Mongo, NOT a fresh AI inference. Every insight is
traceable to a concrete signal in the database.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from db import (
    db as mongo_db,
)
from career_intelligence import CareerIntelligence


MAX_INSIGHTS = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _is_dismissed(user_id: str, insight_id: str) -> bool:
    doc = await mongo_db.insight_dismissals.find_one(
        {"user_id": user_id, "insight_id": insight_id},
        {"_id": 0, "_id_exists": 1},
    )
    return doc is not None


async def _all_dismissed(user_id: str) -> set[str]:
    ids: set[str] = set()
    async for d in mongo_db.insight_dismissals.find(
        {"user_id": user_id}, {"_id": 0, "insight_id": 1}
    ):
        ids.add(d.get("insight_id"))
    return ids


def _shape(
    insight_id: str,
    kind: str,
    headline: str,
    detail: str,
    *,
    source_signals: list[str],
    confidence: int,
    action_label: str,
    action_route: str,
    tone: str = "neutral",
) -> dict[str, Any]:
    return {
        "id":             insight_id,
        "kind":           kind,
        "headline":       headline,
        "detail":         detail,
        "source_signals": source_signals,
        "confidence":     max(0, min(100, int(confidence))),
        "tone":           tone,  # neutral | positive | caution
        "suggested_action": {"label": action_label, "route": action_route},
        "dismissible":    True,
        "created_at":     _now(),
    }


async def build_insights(user_id: str) -> list[dict[str, Any]]:
    """Aggregate active orchestration outputs into a small list of Insight cards.

    Order of precedence (most strategic first):
      1. Salary comparison on a recent offer (offer_received)
      2. Skill-gap review hint (job_rejected pattern)
      3. Interview prep pre-fill (recruiter_reachout)
      4. CV tailor hint (bookmark_added)
      5. Derived signals (CareerIntelligence.cross_feature_signals)
    """
    insights: list[dict[str, Any]] = []
    dismissed = await _all_dismissed(user_id)

    # 1. SALARY COMPARISON — most strategic when present
    async for sc in mongo_db.salary_comparison.find(
        {"user_id": user_id, "needs_comparison": True}, {"_id": 0}
    ).limit(2):
        iid = f"salary_comparison:{sc.get('company', '?')}"
        if iid in dismissed:
            continue
        company = sc.get("company") or "this company"
        ins = _shape(
            iid,
            "salary_comparison",
            f"New offer from {company} — let's benchmark it.",
            "An offer was received recently. Compare against market data and your modeled trajectory before responding.",
            source_signals=[
                f"offer_received event (company={company})",
                "salary_cache market data available",
            ],
            confidence=80,
            action_label="Run salary check",
            action_route="/salary",
            tone="positive",
        )
        insights.append(ins)

    # 2. SKILL-GAP REVIEW — from rejection pattern
    if "skill_gap_review:active" not in dismissed:
        hint = await mongo_db.workflow_hints.find_one(
            {"user_id": user_id, "kind": "skill_gap_review", "active": True},
            {"_id": 0},
        )
        if hint:
            iid = "skill_gap_review:active"
            ci = CareerIntelligence(user_id)
            signals = await ci.cross_feature_signals()
            gaps = signals.get("skill_gaps_from_rejections", [])[:3]
            gap_line = ", ".join(gaps) if gaps else "common required skills"
            ins = _shape(
                iid,
                "skill_gap_review",
                f"You've been passed on roles requiring {gap_line}.",
                "A pattern of rejections is forming around specific skills. Reviewing your skill-gap profile may unlock the next interview round.",
                source_signals=[
                    "job_rejected event(s) in last 30 days",
                    f"top required skill(s) missing: {gap_line}",
                ],
                confidence=72,
                action_label="See skill gaps",
                action_route="/decision",
                tone="caution",
            )
            insights.append(ins)

    # 3. INTERVIEW PREP PRE-FILL — from recruiter reachout
    async for ipc in mongo_db.interview_prep_context.find(
        {"user_id": user_id, "consumed": False}, {"_id": 0}
    ).sort("seeded_at", -1).limit(2):
        iid = f"interview_prep:{ipc.get('from_addr', '?')}"
        if iid in dismissed:
            continue
        who = ipc.get("from_name") or ipc.get("from_addr") or "a recruiter"
        ins = _shape(
            iid,
            "interview_prep_prefill",
            f"{who} reached out — we've prepped context.",
            (ipc.get("intent") or "We've pre-loaded company research and likely questions for this conversation.")[:160],
            source_signals=[
                f"recruiter_reachout email from {who}",
                "interview_prep_context seeded by orchestrator",
            ],
            confidence=70,
            action_label="Open interview prep",
            action_route="/interview-prep",
            tone="neutral",
        )
        insights.append(ins)

    # 4. CV TAILOR HINT — from bookmarks
    async for hint in mongo_db.cv_tailor_hints.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    ).sort("created_at", -1).limit(2):
        iid = f"cv_tailor:{hint.get('job_id', '?')}"
        if iid in dismissed:
            continue
        title = hint.get("job_title") or "the role"
        company = hint.get("company") or "the company"
        ins = _shape(
            iid,
            "cv_tailor_prefill",
            f"Tailor your CV for {title} at {company}?",
            "You bookmarked this role. We can pre-load it into CV Tailor so you don't start from a blank page.",
            source_signals=[
                "bookmark_added event",
                "no CV version exists yet for this job",
            ],
            confidence=65,
            action_label="Tailor my CV",
            action_route=f"/cv-tailor?job_id={hint.get('job_id', '')}",
            tone="neutral",
        )
        insights.append(ins)

    # 5. DERIVED SIGNALS — interview performance fall-off, high-interest companies
    if len(insights) < MAX_INSIGHTS:
        try:
            ci = CareerIntelligence(user_id)
            signals = await ci.cross_feature_signals()
            companies = signals.get("high_interest_companies", [])[:3]
            if companies and "high_interest_companies:strategic" not in dismissed:
                ins = _shape(
                    "high_interest_companies:strategic",
                    "high_interest_companies",
                    f"Recruiters at {', '.join(companies)} have engaged you recently.",
                    "These companies have shown active interest. A short, targeted follow-up tends to convert at much higher rates than cold applications.",
                    source_signals=[
                        f"recruiter_reachout email(s) from: {', '.join(companies)}",
                    ],
                    confidence=68,
                    action_label="Open inbox",
                    action_route="/emails",
                    tone="positive",
                )
                insights.append(ins)
        except Exception:
            pass

    # Cap and return
    return insights[:MAX_INSIGHTS]


async def dismiss_insight(user_id: str, insight_id: str) -> None:
    """Record a dismissal so the same insight doesn't reappear."""
    await mongo_db.insight_dismissals.update_one(
        {"user_id": user_id, "insight_id": insight_id},
        {"$set": {
            "user_id":    user_id,
            "insight_id": insight_id,
            "dismissed_at": _now(),
        }},
        upsert=True,
    )

    # Also mark source records as consumed where appropriate (clean handoff)
    if insight_id.startswith("interview_prep:"):
        from_addr = insight_id.split(":", 1)[1]
        await mongo_db.interview_prep_context.update_many(
            {"user_id": user_id, "from_addr": from_addr},
            {"$set": {"consumed": True}},
        )
    elif insight_id.startswith("cv_tailor:"):
        job_id = insight_id.split(":", 1)[1]
        await mongo_db.cv_tailor_hints.update_one(
            {"user_id": user_id, "job_id": job_id},
            {"$set": {"active": False}},
        )
    elif insight_id == "skill_gap_review:active":
        await mongo_db.workflow_hints.update_one(
            {"user_id": user_id, "kind": "skill_gap_review"},
            {"$set": {"active": False}},
        )
    elif insight_id.startswith("salary_comparison:"):
        company = insight_id.split(":", 1)[1]
        await mongo_db.salary_comparison.update_one(
            {"user_id": user_id, "company": company},
            {"$set": {"needs_comparison": False}},
        )
