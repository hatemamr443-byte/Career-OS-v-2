"""
Career Intelligence Layer — The Unified Brain of Career OS.

Every feature writes to and reads from this layer.
This is what makes Career OS feel like ONE system, not many disconnected tools.

Architecture:
  - Career Graph: persistent nodes (skills, companies, roles, outcomes)
  - Behavioral Memory: patterns extracted from user actions
  - Cross-Feature Signals: job match ↔ CV tailor ↔ interview ↔ salary
  - Event-Driven Updates: every action enriches the graph

Usage:
  from career_intelligence import CareerIntelligence

  ci = CareerIntelligence(user_id)
  context = await ci.get_context()          # Full career context for LLM calls
  await ci.record_event("job_applied", {...})  # Update graph
  signals = await ci.cross_feature_signals()   # Signals for feature coordination
"""
from datetime import datetime, timezone, timedelta
from db import (
    profiles, applications, jobs, activity_logs,
    xp_events, cv_versions, interview_sessions,
    db as mongo_db,
)
import logging

logger = logging.getLogger(__name__)

career_graph = mongo_db.career_graph       # persistent career graph nodes
career_events = mongo_db.career_events    # event stream for the graph


class CareerIntelligence:
    """
    Unified intelligence context for a single user.
    Instantiate per-request; reads from MongoDB.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def get_context(self, depth: str = "standard") -> dict:
        """
        Build a rich career context dict for LLM system prompts.
        depth="minimal"  → skills + target only (fast)
        depth="standard" → adds history + patterns (most calls)
        depth="full"     → adds everything including memory (coach calls)
        """
        uid = self.user_id
        profile = await profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
        user_doc = await mongo_db.users.find_one({"user_id": uid}, {"_id": 0}) or {}

        ctx = {
            "user": {
                "level":   user_doc.get("level", 1),
                "streak":  user_doc.get("streak", 0),
            },
            "profile": {
                "skills":           profile.get("skills", []),
                "target_roles":     profile.get("target_roles", []),
                "target_locations": profile.get("target_locations", []),
                "years_experience": profile.get("years_experience", 0),
                "salary_min":       profile.get("salary_min"),
                "headline":         profile.get("headline", ""),
                "cv_snippet":       (profile.get("cv_text") or "")[:600],
            },
        }

        if depth in ("standard", "full"):
            # Application history patterns
            apps = await applications.find(
                {"user_id": uid}, {"_id": 0}
            ).sort("created_at", -1).limit(50).to_list(50)

            outcome_counts = {"offer": 0, "rejected": 0, "interview": 0, "applied": 0}
            recent_companies = []
            rejected_roles   = []
            interview_rates_by_seniority: dict[str, list] = {}

            for app in apps:
                status = app.get("status", "")
                if status in outcome_counts:
                    outcome_counts[status] += 1

                if app.get("job", {}).get("company"):
                    recent_companies.append(app["job"]["company"])

                if status == "rejected" and app.get("job", {}).get("title"):
                    rejected_roles.append(app["job"]["title"])

            ctx["application_history"] = {
                "total":           len(apps),
                "outcomes":        outcome_counts,
                "recent_companies": list(set(recent_companies))[:8],
                "rejected_roles":  rejected_roles[:5],
                "interview_rate":  round(
                    100 * outcome_counts["interview"] / max(outcome_counts["applied"], 1), 1
                ),
            }

            # CV version intelligence
            cv_vers = await cv_versions.find(
                {"user_id": uid}, {"_id": 0, "keywords_added": 1, "job_title": 1}
            ).sort("created_at", -1).limit(10).to_list(10)

            all_added_keywords = []
            for v in cv_vers:
                all_added_keywords.extend(v.get("keywords_added", []))

            ctx["cv_intelligence"] = {
                "tailored_versions": len(cv_vers),
                "commonly_added_keywords": list(set(all_added_keywords))[:15],
                "recent_target_roles": [v.get("job_title") for v in cv_vers if v.get("job_title")][:5],
            }

        if depth == "full":
            # Interview performance memory
            sessions = await interview_sessions.find(
                {"user_id": uid}, {"_id": 0}
            ).sort("created_at", -1).limit(5).to_list(5)

            weak_areas = []
            strong_areas = []
            for sess in sessions:
                for q_id, eval_data in (sess.get("evaluations") or {}).items():
                    if isinstance(eval_data, dict):
                        score = eval_data.get("score", 5)
                        q_text = ""
                        for q in (sess.get("questions") or []):
                            if isinstance(q, dict) and q.get("id") == q_id:
                                q_text = q.get("type", "")
                        if score >= 8:
                            strong_areas.append(q_text or "unknown")
                        elif score <= 5:
                            weak_areas.append(q_text or "unknown")

            ctx["interview_memory"] = {
                "sessions_completed": len(sessions),
                "strong_areas":       strong_areas[:5],
                "weak_areas":         weak_areas[:5],
            }

            # Behavioral patterns from activity
            recent_events = await activity_logs.find(
                {"user_id": uid}, {"_id": 0, "event_type": 1}
            ).sort("created_at", -1).limit(30).to_list(30)

            event_freq: dict[str, int] = {}
            for ev in recent_events:
                t = ev.get("event_type", "unknown")
                event_freq[t] = event_freq.get(t, 0) + 1

            ctx["behavior_patterns"] = {
                "event_frequency": event_freq,
                "most_active_feature": max(event_freq, key=event_freq.get) if event_freq else None,
            }

            # Long-term memory from career_graph
            graph_node = await career_graph.find_one({"user_id": uid}, {"_id": 0}) or {}
            ctx["career_memory"] = {
                "preferred_company_types":  graph_node.get("preferred_company_types", []),
                "avoided_industries":       graph_node.get("avoided_industries", []),
                "successful_skill_clusters": graph_node.get("successful_skill_clusters", []),
                "salary_trajectory":        graph_node.get("salary_trajectory", []),
                "notes":                    graph_node.get("ai_notes", ""),
            }

        return ctx

    async def get_context_prompt(self, depth: str = "standard") -> str:
        """Return career context formatted for LLM system prompt injection."""
        ctx = await self.get_context(depth)
        p = ctx.get("profile", {})
        h = ctx.get("application_history", {})
        cv = ctx.get("cv_intelligence", {})
        im = ctx.get("interview_memory", {})
        cm = ctx.get("career_memory", {})

        lines = [
            "## User Career Context (use this to personalize all responses)",
            f"Skills: {', '.join(p.get('skills', [])) or 'not set'}",
            f"Target roles: {', '.join(p.get('target_roles', [])) or 'not set'}",
            f"Target locations: {', '.join(p.get('target_locations', [])) or 'not set'}",
            f"Experience: {p.get('years_experience', 0)} years",
            f"Salary expectation: {p.get('salary_min', 'not set')}",
        ]

        if h:
            lines += [
                f"Applications sent: {h.get('total', 0)}",
                f"Interview rate: {h.get('interview_rate', 0)}%",
                f"Recent companies: {', '.join(h.get('recent_companies', [])[:4]) or 'none'}",
            ]

        if cv and cv.get("commonly_added_keywords"):
            lines.append(f"CV gaps being addressed: {', '.join(cv['commonly_added_keywords'][:8])}")

        if im and im.get("weak_areas"):
            lines.append(f"Interview areas to improve: {', '.join(im['weak_areas'][:3])}")

        if cm and cm.get("notes"):
            lines.append(f"Career memory: {cm['notes']}")

        return "\n".join(lines)

    async def record_event(self, event_type: str, data: dict) -> None:
        """Record a career event and update the graph node."""
        now = datetime.now(timezone.utc).isoformat()
        await career_events.insert_one({
            "user_id":    self.user_id,
            "event_type": event_type,
            "data":       data,
            "created_at": now,
        })
        # Update graph for significant events
        if event_type == "job_rejected":
            await career_graph.update_one(
                {"user_id": self.user_id},
                {"$addToSet": {"rejected_job_ids": data.get("job_id")},
                 "$set":      {"updated_at": now}},
                upsert=True,
            )
        elif event_type == "offer_received":
            await career_graph.update_one(
                {"user_id": self.user_id},
                {"$push": {"salary_trajectory": {
                    "amount": data.get("salary"), "date": now,
                    "company": data.get("company"),
                }}},
                upsert=True,
            )
        elif event_type == "interview_completed":
            score = data.get("average_score", 0)
            if score >= 8:
                await career_graph.update_one(
                    {"user_id": self.user_id},
                    {"$addToSet": {"successful_skill_clusters": {"$each": data.get("strong_skills", [])}}},
                    upsert=True,
                )

    async def cross_feature_signals(self) -> dict:
        """
        Extract signals that flow BETWEEN features.
        This is the core of cohesion — how job matching informs CV tailoring,
        how email patterns inform interview prep, etc.
        """
        uid = self.user_id

        # Signal 1: Skills to add to CV based on rejected jobs
        apps = await applications.find(
            {"user_id": uid, "status": "rejected"}, {"_id": 0, "job_id": 1}
        ).limit(10).to_list(10)

        missing_skills: list[str] = []
        if apps:
            job_ids = [a["job_id"] for a in apps]
            async for j in jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0, "skills_required": 1}):
                missing_skills.extend(j.get("skills_required", []))

        profile = await profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
        my_skills = set(profile.get("skills", []))
        skill_gaps = list(set(missing_skills) - my_skills)[:10]

        # Signal 2: Companies who opened emails → likely interested
        high_interest_companies: list[str] = []
        async for email in mongo_db.emails.find(
            {"user_id": uid, "classification": "recruiter_reachout"},
            {"_id": 0, "from_name": 1, "from_addr": 1}
        ).limit(20):
            name = email.get("from_name", "")
            if name:
                high_interest_companies.append(name)

        # Signal 3: Interview success rate by role type
        sessions = await interview_sessions.find(
            {"user_id": uid}, {"_id": 0, "job_title": 1, "evaluations": 1}
        ).limit(20).to_list(20)

        avg_scores: dict[str, list] = {}
        for s in sessions:
            title = s.get("job_title", "unknown")
            scores = [
                e.get("score", 0)
                for e in (s.get("evaluations") or {}).values()
                if isinstance(e, dict)
            ]
            if scores:
                avg_scores.setdefault(title, []).extend(scores)

        role_scores = {
            role: round(sum(scores) / len(scores), 1)
            for role, scores in avg_scores.items()
        }

        # Signal 4: Salary expectations vs market findings
        salary_insights = await mongo_db.salary_cache.find_one(
            {"user_id": uid}, {"_id": 0, "market_median": 1, "role": 1}
        ) or {}

        return {
            "skill_gaps_from_rejections":    skill_gaps,
            "high_interest_companies":       high_interest_companies[:5],
            "interview_performance_by_role": role_scores,
            "salary_market_context": {
                "role":          salary_insights.get("role"),
                "market_median": salary_insights.get("market_median"),
            },
        }

    async def update_ai_notes(self, notes: str) -> None:
        """Store free-form AI observations about this user's career."""
        await career_graph.update_one(
            {"user_id": self.user_id},
            {"$set": {"ai_notes": notes, "notes_updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )


# ── Convenience function for route injection ───────────────────────

async def get_career_context_prompt(user_id: str, depth: str = "standard") -> str:
    """Quick helper for injecting career context into LLM system prompts."""
    ci = CareerIntelligence(user_id)
    return await ci.get_context_prompt(depth)
