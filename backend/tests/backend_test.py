"""AI Career OS backend tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://job-agent-ai-6.preview.emergentagent.com").rstrip("/")
TOKEN = "test_session_career_os"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session", autouse=True)
def seed_user():
    requests.post(f"{BASE_URL}/api/seed-me", headers=HEADERS, timeout=30)
    yield


# Auth
def test_auth_me():
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user_id"] == "user_testseed01"
    assert data["email"] == "test.career@example.com"


def test_auth_me_unauth():
    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401


# Jobs
def test_list_jobs():
    r = requests.get(f"{BASE_URL}/api/jobs", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 10
    j = data["jobs"][0]
    assert "quick_score" in j and "job_id" in j and "title" in j


def test_job_detail():
    jobs = requests.get(f"{BASE_URL}/api/jobs", headers=HEADERS, timeout=20).json()["jobs"]
    jid = jobs[0]["job_id"]
    r = requests.get(f"{BASE_URL}/api/jobs/{jid}", headers=HEADERS, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["job"]["job_id"] == jid
    assert "application" in data


def test_match_endpoint():
    jobs = requests.get(f"{BASE_URL}/api/jobs", headers=HEADERS, timeout=20).json()["jobs"]
    jid = jobs[0]["job_id"]
    r = requests.post(f"{BASE_URL}/api/jobs/{jid}/match", headers=HEADERS, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "score" in data and "decision" in data and "reasoning" in data
    assert isinstance(data["score"], int) and 0 <= data["score"] <= 100


# Applications
def test_create_and_update_application():
    jobs = requests.get(f"{BASE_URL}/api/jobs", headers=HEADERS, timeout=20).json()["jobs"]
    jid = jobs[1]["job_id"]
    r = requests.post(f"{BASE_URL}/api/applications", json={"job_id": jid}, headers=HEADERS, timeout=20)
    assert r.status_code == 200, r.text
    app = r.json()
    assert app["status"] == "applied"
    assert len(app["timeline"]) >= 2
    aid = app["application_id"]

    # Update
    r2 = requests.patch(f"{BASE_URL}/api/applications/{aid}", json={"status": "interview", "reason": "scheduled"}, headers=HEADERS, timeout=20)
    assert r2.status_code == 200
    upd = r2.json()
    assert upd["status"] == "interview"
    assert any(t["status"] == "interview" for t in upd["timeline"])

    # GET list
    r3 = requests.get(f"{BASE_URL}/api/applications", headers=HEADERS, timeout=20)
    assert r3.status_code == 200
    assert any(a["application_id"] == aid for a in r3.json()["applications"])


def test_recommendations():
    r = requests.get(f"{BASE_URL}/api/decisions/recommendations", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "decision" in rec
        assert rec["decision"]["decision"] in ["apply", "consider", "skip"]


# Emails
def test_emails_list():
    r = requests.get(f"{BASE_URL}/api/emails", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    data = r.json()
    # could be threads grouped
    assert isinstance(data, dict)
    # accept either {threads: [...]} or {emails: [...]}
    items = data.get("threads") or data.get("emails") or []
    assert len(items) >= 1


def test_email_classify():
    r = requests.get(f"{BASE_URL}/api/emails", headers=HEADERS, timeout=20).json()
    items = r.get("threads") or r.get("emails") or []
    # find an email_id
    eid = None
    if items:
        first = items[0]
        eid = first.get("email_id") or (first.get("emails", [{}])[0].get("email_id"))
    if not eid:
        pytest.skip("no emails")
    r2 = requests.post(f"{BASE_URL}/api/emails/{eid}/classify", headers=HEADERS, timeout=60)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert "classification" in d


# Missions
def test_missions_today():
    r = requests.get(f"{BASE_URL}/api/missions/today", headers=HEADERS, timeout=60)
    assert r.status_code == 200
    data = r.json()
    missions = data.get("missions", [])
    assert len(missions) >= 1
    # Idempotent - second call should return same number
    r2 = requests.get(f"{BASE_URL}/api/missions/today", headers=HEADERS, timeout=20)
    assert len(r2.json().get("missions", [])) == len(missions)


def test_complete_mission_and_stats():
    missions = requests.get(f"{BASE_URL}/api/missions/today", headers=HEADERS, timeout=30).json().get("missions", [])
    if not missions:
        pytest.skip("no missions")
    # find an incomplete one
    target = next((m for m in missions if not m.get("completed")), missions[0])
    mid = target.get("mission_id") or target.get("id")
    pre = requests.get(f"{BASE_URL}/api/me/stats", headers=HEADERS, timeout=15).json()
    r = requests.post(f"{BASE_URL}/api/missions/{mid}/complete", headers=HEADERS, timeout=20)
    assert r.status_code == 200, r.text
    post = requests.get(f"{BASE_URL}/api/me/stats", headers=HEADERS, timeout=15).json()
    assert post.get("xp", 0) >= pre.get("xp", 0)


def test_stats():
    r = requests.get(f"{BASE_URL}/api/me/stats", headers=HEADERS, timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["xp", "level", "streak"]:
        assert k in d


# Coach
def test_coach_chat():
    r = requests.get(f"{BASE_URL}/api/coach/messages", headers=HEADERS, timeout=15)
    assert r.status_code == 200
    r2 = requests.post(f"{BASE_URL}/api/coach/chat", json={"message": "Give me one quick tip"}, headers=HEADERS, timeout=90)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d.get("reply") or d.get("message") or d.get("content")


# Insights
def test_insights():
    r = requests.get(f"{BASE_URL}/api/insights", headers=HEADERS, timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert "totals" in d or "funnel" in d


# Profile
def test_profile_get_update():
    r = requests.get(f"{BASE_URL}/api/profile", headers=HEADERS, timeout=15)
    assert r.status_code == 200
    p = r.json()
    assert "skills" in p
    r2 = requests.put(f"{BASE_URL}/api/profile", json={"headline": "Updated headline TEST"}, headers=HEADERS, timeout=15)
    assert r2.status_code == 200
    p2 = requests.get(f"{BASE_URL}/api/profile", headers=HEADERS, timeout=15).json()
    assert p2.get("headline") == "Updated headline TEST"
