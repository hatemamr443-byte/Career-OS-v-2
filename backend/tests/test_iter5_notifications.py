"""Iter5: Daily digest + cron endpoint + asyncio.gather ingest parallelism tests."""
import os
import time
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://job-agent-ai-6.preview.emergentagent.com").rstrip("/")
TOKEN = "test_session_career_os"
USER_ID = "user_testseed01"
CRON_TOKEN = "local_dev_cron_secret_12345"

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Direct Mongo handle for setup/teardown of last_email_sent
_mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
_db = _mongo[os.environ.get("DB_NAME", "test_database")]


@pytest.fixture(autouse=True)
def _reset_last_email_sent():
    # Ensure 20h gate isn't blocking unless test explicitly sets it
    _db.profiles.update_one(
        {"user_id": USER_ID},
        {"$unset": {"last_email_sent": ""}},
    )
    yield


# ───── Notifications toggle ─────
class TestNotificationsToggle:
    def test_enable_daily_matches(self):
        r = requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": True})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["daily_matches"] is True
        assert data["email_configured"] is False  # RESEND_API_KEY blank by-design
        assert isinstance(data["email_target"], str) and "@" in data["email_target"]

        # Verify persisted in DB
        prof = _db.profiles.find_one({"user_id": USER_ID})
        assert prof is not None
        assert prof.get("daily_matches") is True

    def test_disable_daily_matches(self):
        r = requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": False})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["daily_matches"] is False
        assert data["email_configured"] is False
        # Verify persisted
        prof = _db.profiles.find_one({"user_id": USER_ID})
        assert prof.get("daily_matches") is False


# ───── Manual test digest endpoint ─────
class TestSendTestDigest:
    def test_test_digest_when_off_returns_skipped(self):
        # Turn off
        requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": False})
        r = requests.post(f"{BASE_URL}/api/profile/notifications/test", headers=HEADERS, json={})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("skipped") is True
        assert "daily_matches OFF" in data.get("reason", "")

    def test_test_digest_when_on_graceful_no_key(self):
        # Turn on
        requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": True})
        r = requests.post(f"{BASE_URL}/api/profile/notifications/test", headers=HEADERS, json={})
        assert r.status_code == 200, r.text
        data = r.json()
        # Either sent:false with RESEND reason, or skipped because no matching jobs
        if data.get("skipped"):
            assert data.get("reason") in ("no matching jobs", "no profile")
        else:
            assert data.get("sent") is False
            assert "RESEND_API_KEY not configured" in data.get("reason", "")
            assert data.get("jobs_sent", 0) >= 1

    def test_20h_gate_blocks_resend(self):
        # Enable
        requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": True})
        # Force last_email_sent = now
        _db.profiles.update_one(
            {"user_id": USER_ID},
            {"$set": {"last_email_sent": datetime.now(timezone.utc).isoformat()}},
        )
        r = requests.post(f"{BASE_URL}/api/profile/notifications/test", headers=HEADERS, json={})
        assert r.status_code == 200
        data = r.json()
        assert data.get("skipped") is True
        assert "20h" in data.get("reason", "") or "last_email_sent" in data.get("reason", "")


# ───── Cron endpoint ─────
class TestCronEndpoint:
    def test_cron_no_token_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/internal/run-daily-digest")
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_cron_wrong_token_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/internal/run-daily-digest", headers={"X-Cron-Token": "wrong"})
        assert r.status_code == 401

    def test_cron_valid_token_returns_200(self):
        # Ensure at least our test user is opted-in
        requests.put(f"{BASE_URL}/api/profile/notifications", headers=HEADERS, json={"daily_matches": True})
        r = requests.post(f"{BASE_URL}/api/internal/run-daily-digest", headers={"X-Cron-Token": CRON_TOKEN}, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "users_processed" in data
        assert "sent" in data
        assert "skipped" in data
        assert "results" in data
        assert isinstance(data["results"], list)


# ───── render_daily_digest pure function ─────
class TestRenderDigest:
    def test_render_returns_html_and_text(self):
        # conftest.py already adds backend/ to sys.path — import directly
        from emailer import render_daily_digest

        jobs = [
            {"title": "Senior Python Engineer", "company": "Acme Co", "location": "Lisbon",
             "quick_score": 87, "source_url": "https://example.com/job/1"},
            {"title": "Backend Developer", "company": "Globex", "location": "Remote",
             "quick_score": 72, "source_url": "https://example.com/job/2"},
        ]
        html, text = render_daily_digest("Alex Tester", jobs, "https://app.example.com")
        assert isinstance(html, str) and len(html) > 100
        assert isinstance(text, str) and len(text) > 0
        # Required content
        assert "Alex Tester" in html
        assert "Senior Python Engineer" in html
        assert "Acme Co" in html
        assert "87" in html  # match score
        assert "https://example.com/job/1" in html  # apply link
        # Plain text version
        assert "Senior Python Engineer" in text
        assert "Acme Co" in text


# ───── Parallel ingest (asyncio.gather) ─────
class TestIngestParallelism:
    def test_ingest_completes_under_30s(self):
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/jobs/ingest", headers=HEADERS, json={"query": "python", "limit": 10}, timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        assert elapsed < 30, f"ingest took {elapsed:.1f}s, expected <30s (parallel)"
        data = r.json()
        # New format: {total_inserted, by_source, errors} OR legacy shim
        assert ("by_source" in data) or ("inserted" in data)


# ───── Regression on previous iter endpoints ─────
class TestRegression:
    def test_me_usage(self):
        r = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS)
        assert r.status_code == 200

    def test_billing_me(self):
        r = requests.get(f"{BASE_URL}/api/billing/me", headers=HEADERS)
        assert r.status_code == 200

    def test_auth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data.get("user_id") == USER_ID
