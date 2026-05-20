"""
Iteration 9 — Brain Reveal layer backend tests.

Covers:
  - /api/orchestrator/insights — auth gate (401 unauthenticated)
  - /api/orchestrator/insights/{id}/dismiss — auth gate (401 unauthenticated)
  - /api/orchestrator/health — still works with 6 subscribers
  - /api/decision/* — auth gates intact (no regression)
  - legacy routes (/api/jobs, /api/applications, /api/emails) — auth gates intact
  - insight shape — verified via code review of insights_service._shape()
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://job-agent-ai-6.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ────────────────────────────────────────
# New Brain Reveal endpoints — auth gates
# ────────────────────────────────────────
class TestInsightsAuthGate:
    def test_insights_get_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/orchestrator/insights", timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_insights_get_with_invalid_token_unauth(self, session):
        r = session.get(
            f"{BASE_URL}/api/orchestrator/insights",
            headers={"Authorization": "Bearer invalid-token-xyz"},
            timeout=15,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_insights_dismiss_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/orchestrator/insights/test_id_123/dismiss",
            timeout=15,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_insights_dismiss_url_encoded_id_requires_auth(self, session):
        # id can contain colons (e.g., 'salary_comparison:Acme') — must still 401
        r = session.post(
            f"{BASE_URL}/api/orchestrator/insights/salary_comparison%3AAcme/dismiss",
            timeout=15,
        )
        assert r.status_code == 401


# ────────────────────────────────────────
# Health endpoint regression
# ────────────────────────────────────────
class TestOrchestratorHealth:
    def test_health_still_works(self, session):
        r = session.get(f"{BASE_URL}/api/orchestrator/health", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        bus = body.get("bus", {})
        subs = bus.get("subscribers", {})
        required = [
            "job_rejected", "interview_completed", "offer_received",
            "job_applied", "recruiter_reachout", "bookmark_added",
        ]
        for key in required:
            assert key in subs, f"missing subscriber: {key}"
            assert subs[key] >= 1


# ────────────────────────────────────────
# Decision routes regression — auth gates intact
# ────────────────────────────────────────
class TestDecisionRoutesAuthGates:
    def test_decision_match_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/decision/match/test_job_id",
            timeout=15,
        )
        assert r.status_code == 401

    def test_decision_career_roi_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/decision/career-roi",
            json={"job_id": "x"},
            timeout=15,
        )
        assert r.status_code == 401

    def test_decision_strategic_plan_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/strategic-plan", timeout=15)
        assert r.status_code == 401

    def test_decision_wellbeing_check_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/wellbeing-check", timeout=15)
        assert r.status_code == 401

    def test_decision_skill_gaps_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/skill-gaps", timeout=15)
        assert r.status_code == 401


# ────────────────────────────────────────
# Legacy routes regression — auth gates intact
# ────────────────────────────────────────
class TestLegacyRoutesAuthGates:
    def test_jobs_list_does_not_500(self, session):
        # /api/jobs may be public listing OR auth-gated; either way it must not 500
        r = session.get(f"{BASE_URL}/api/jobs", timeout=15)
        assert r.status_code in (200, 401, 403), f"unexpected {r.status_code}"

    def test_applications_get_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/applications", timeout=15)
        assert r.status_code == 401

    def test_applications_post_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/applications",
            json={"job_id": "x"},
            timeout=15,
        )
        assert r.status_code == 401

    def test_emails_get_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/emails", timeout=15)
        assert r.status_code == 401


# ────────────────────────────────────────
# Insight shape — verified via static code review of build_insights/_shape
# ────────────────────────────────────────
class TestInsightShape:
    def test_shape_helper_emits_required_keys(self):
        """Static guarantee: insights_service._shape() emits the spec keys."""
        from insights_service import _shape
        ins = _shape(
            "test_id",
            "test_kind",
            "head",
            "detail",
            source_signals=["sig"],
            confidence=80,
            action_label="Open",
            action_route="/x",
            tone="positive",
        )
        required = {
            "id", "kind", "headline", "detail", "source_signals",
            "confidence", "tone", "suggested_action", "dismissible",
            "created_at",
        }
        missing = required - set(ins.keys())
        assert not missing, f"missing keys: {missing}"
        assert isinstance(ins["source_signals"], list)
        assert 0 <= ins["confidence"] <= 100
        assert ins["tone"] in {"neutral", "positive", "caution"}
        assert "label" in ins["suggested_action"]
        assert "route" in ins["suggested_action"]
        assert ins["dismissible"] is True

    def test_max_insights_constant_is_5(self):
        from insights_service import MAX_INSIGHTS
        assert MAX_INSIGHTS == 5
