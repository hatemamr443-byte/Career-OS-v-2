"""
Iteration 8 — P1 Brain Activation backend tests.

Covers:
  - /api/orchestrator/health (6 subscribers, emergent llm ok)
  - /api/orchestrator/telemetry (auth + shape)
  - /api/orchestrator/memory + /api/orchestrator/recent-events (auth gate)
  - /api/decision/* migrated routes (route mount + auth gate)
  - /api/applications, /api/bookmarks, /api/emails (still mount)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ────────────────────────────────────────
# Orchestrator health
# ────────────────────────────────────────
class TestOrchestratorHealth:
    def test_health_ok_and_subscribers(self, session):
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
            assert key in subs, f"missing subscriber: {key} (have {list(subs.keys())})"
            assert subs[key] >= 1, f"subscriber {key} count must be >=1, got {subs[key]}"

        llm = body.get("llm", {})
        providers = llm.get("providers", {})
        assert providers.get("emergent") == "ok", f"emergent provider not ok: {providers}"
        assert llm.get("any_available") is True


# ────────────────────────────────────────
# Orchestrator telemetry (auth)
# ────────────────────────────────────────
class TestOrchestratorTelemetry:
    def test_telemetry_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/orchestrator/telemetry", timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code} body={r.text[:200]}"

    def test_memory_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/orchestrator/memory", timeout=15)
        assert r.status_code == 401

    def test_recent_events_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/orchestrator/recent-events", timeout=15)
        assert r.status_code == 401


# ────────────────────────────────────────
# Decision Engine routes — auth gate
# ────────────────────────────────────────
class TestDecisionRoutes:
    def test_match_requires_auth(self, session):
        r = session.post(f"{BASE_URL}/api/decision/match/some_job", timeout=15)
        assert r.status_code == 401, f"got {r.status_code} body={r.text[:200]}"

    def test_career_roi_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/decision/career-roi",
            json={"job_ids": ["a", "b"]},
            timeout=15,
        )
        assert r.status_code == 401

    def test_strategic_plan_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/strategic-plan", timeout=15)
        assert r.status_code == 401

    def test_wellbeing_check_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/wellbeing-check", timeout=15)
        assert r.status_code == 401

    def test_skill_gaps_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/decision/skill-gaps", timeout=15)
        assert r.status_code == 401


# ────────────────────────────────────────
# Jobs / bookmarks / emails — still mounted
# ────────────────────────────────────────
class TestExistingRoutesStillMount:
    def test_applications_create_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/applications",
            json={"job_id": "fake_job"},
            timeout=15,
        )
        # Must be 401 (auth gate), not 404 (route lost)
        assert r.status_code == 401, f"got {r.status_code} body={r.text[:200]}"

    def test_applications_patch_requires_auth(self, session):
        r = session.patch(
            f"{BASE_URL}/api/applications/fake_id",
            json={"status": "applied"},
            timeout=15,
        )
        assert r.status_code == 401

    def test_bookmarks_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/bookmarks/fake_job_id",
            timeout=15,
        )
        assert r.status_code == 401

    def test_email_classify_requires_auth(self, session):
        r = session.post(
            f"{BASE_URL}/api/emails/fake_email_id/classify",
            timeout=15,
        )
        assert r.status_code == 401
