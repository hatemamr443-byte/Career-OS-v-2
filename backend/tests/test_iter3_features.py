"""Iteration 3: quota gating, billing cancel, PDF upload, Remotive ingest."""
import io
import os
import pytest
import requests
from pymongo import MongoClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://job-agent-ai-6.preview.emergentagent.com").rstrip("/")
TOKEN = os.environ.get("TEST_SESSION_TOKEN", "test_session_career_os")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
JSON_HEADERS = {**HEADERS, "Content-Type": "application/json"}
USER_ID = "user_testseed01"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]


def _reset_quota():
    _db.match_usage.delete_many({"user_id": USER_ID})
    _db.decisions.delete_many({"user_id": USER_ID})


def _set_plan_free():
    _db.users.update_one(
        {"user_id": USER_ID},
        {"$set": {"plan": "free"},
         "$unset": {"plan_expires_at": "", "cancelled_at": "", "previous_plan": ""}},
    )


def _set_plan_pro():
    from datetime import datetime, timezone, timedelta
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    _db.users.update_one(
        {"user_id": USER_ID},
        {"$set": {"plan": "pro", "plan_expires_at": exp}},
    )


@pytest.fixture(scope="session", autouse=True)
def _seed():
    requests.post(f"{BASE_URL}/api/seed-me", headers=JSON_HEADERS, timeout=30)
    yield


# ---------- /api/me/usage ----------
class TestUsage:
    def test_usage_free_shape(self):
        _set_plan_free()
        _reset_quota()
        r = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["plan", "matches_used", "matches_limit", "remaining", "over_limit", "near_limit"]:
            assert k in d, f"missing key {k}: {d}"
        assert d["plan"] == "free"
        assert d["matches_limit"] == 5
        assert d["matches_used"] == 0
        assert d["remaining"] == 5
        assert d["over_limit"] is False
        assert d["near_limit"] is False

    def test_usage_pro_unlimited(self):
        _set_plan_pro()
        r = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["plan"] == "pro"
        assert d["matches_limit"] is None
        assert d["remaining"] is None
        assert d["over_limit"] is False


# ---------- quota gating ----------
class TestQuotaGating:
    def _job_ids(self, n):
        r = requests.get(f"{BASE_URL}/api/jobs?limit=50", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        jobs = r.json()["jobs"]
        assert len(jobs) >= n, f"need {n} jobs, have {len(jobs)}"
        return [j["job_id"] for j in jobs[:n]]

    def test_cached_match_does_not_count(self):
        _set_plan_free()
        _reset_quota()
        jid = self._job_ids(1)[0]
        r1 = requests.post(f"{BASE_URL}/api/jobs/{jid}/match", headers=HEADERS, timeout=120)
        assert r1.status_code == 200, r1.text
        used1 = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15).json()["matches_used"]
        # 2nd call same job — cached
        r2 = requests.post(f"{BASE_URL}/api/jobs/{jid}/match", headers=HEADERS, timeout=60)
        assert r2.status_code == 200
        used2 = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15).json()["matches_used"]
        assert used2 == used1, f"cached match incremented usage: {used1} -> {used2}"
        assert used1 == 1

    def test_quota_blocks_6th_distinct_match(self):
        _set_plan_free()
        _reset_quota()
        jids = self._job_ids(6)
        # 5 distinct succeed
        for i, jid in enumerate(jids[:5]):
            r = requests.post(f"{BASE_URL}/api/jobs/{jid}/match", headers=HEADERS, timeout=120)
            assert r.status_code == 200, f"match #{i+1} failed: {r.status_code} {r.text[:200]}"
        # 6th blocked
        r6 = requests.post(f"{BASE_URL}/api/jobs/{jids[5]}/match", headers=HEADERS, timeout=30)
        assert r6.status_code == 403, f"expected 403 on 6th match, got {r6.status_code}: {r6.text}"
        body = r6.json()
        detail = body.get("detail", body)
        assert detail.get("code") == "quota_exceeded", detail
        assert "5" in detail.get("message", ""), detail
        # usage reflects 5
        u = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15).json()
        assert u["matches_used"] == 5
        assert u["over_limit"] is True
        assert u["remaining"] == 0

    def test_pro_user_unlimited_match(self):
        _set_plan_pro()
        _reset_quota()
        jids = TestQuotaGating._job_ids(self, 1)
        # even if usage > 5 historically, pro should pass — call once
        r = requests.post(f"{BASE_URL}/api/jobs/{jids[0]}/match", headers=HEADERS, timeout=120)
        assert r.status_code == 200, r.text


# ---------- billing cancel ----------
class TestBillingCancel:
    def test_cancel_downgrades_pro_to_free(self):
        _set_plan_pro()
        r = requests.post(f"{BASE_URL}/api/billing/cancel", headers=JSON_HEADERS, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan"] == "free"
        # verify DB state
        u = _db.users.find_one({"user_id": USER_ID})
        assert u["plan"] == "free"
        assert u.get("plan_expires_at") is None
        assert u.get("cancelled_at")
        assert u.get("previous_plan") == "pro"
        # billing/me reflects it
        me = requests.get(f"{BASE_URL}/api/billing/me", headers=HEADERS, timeout=15).json()
        assert me["plan"] == "free"

    def test_cancel_on_free_is_idempotent(self):
        _set_plan_free()
        r = requests.post(f"{BASE_URL}/api/billing/cancel", headers=JSON_HEADERS, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["plan"] == "free"
        assert "Already on Free" in d.get("message", "")


# ---------- PDF upload ----------
def _make_pdf(text: str = "John Doe\nSenior Python Engineer with 8 years building scalable backends. Skills: python, fastapi, mongodb, kubernetes, react, aws. Email: john@example.com. Experience leading teams at Stripe and Airbnb. Built distributed systems handling 10M+ requests.") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 750
    for line in text.split("\n"):
        c.drawString(72, y, line)
        y -= 18
    # Pad to make >100 chars extracted
    for i in range(20):
        c.drawString(72, y, f"Bullet {i}: delivered features, mentored engineers, shipped reliably.")
        y -= 14
    c.showPage()
    c.save()
    return buf.getvalue()


class TestPdfUpload:
    def test_upload_valid_pdf(self):
        _set_plan_free()
        pdf = _make_pdf()
        files = {"file": ("test_cv.pdf", pdf, "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/profile/upload-cv", headers=HEADERS, files=files, timeout=120)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p.get("cv_filename") == "test_cv.pdf"
        assert p.get("cv_bytes") == len(pdf)
        assert "headline" in p
        assert isinstance(p.get("skills"), list)
        assert isinstance(p.get("target_roles"), list)

    def test_reject_non_pdf(self):
        files = {"file": ("resume.txt", b"hello world this is not a pdf", "text/plain")}
        r = requests.post(f"{BASE_URL}/api/profile/upload-cv", headers=HEADERS, files=files, timeout=30)
        assert r.status_code == 400, r.text

    def test_reject_oversized(self):
        big = b"%PDF-1.4\n" + (b"A" * (6 * 1024 * 1024))
        files = {"file": ("big.pdf", big, "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/profile/upload-cv", headers=HEADERS, files=files, timeout=30)
        assert r.status_code == 400, r.text

    def test_reject_empty(self):
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/profile/upload-cv", headers=HEADERS, files=files, timeout=30)
        assert r.status_code == 400, r.text


# ---------- Remotive ingest ----------
class TestRemotiveIngest:
    def test_ingest_returns_counts(self):
        r = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "engineering", "limit": 10},
            headers=JSON_HEADERS,
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["fetched", "inserted", "skipped_duplicates"]:
            assert k in d, f"missing key {k}: {d}"
        assert d["fetched"] >= 1
        assert d["inserted"] + d["skipped_duplicates"] == d["fetched"]

    def test_dedupe_on_second_call(self):
        r1 = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "engineering", "limit": 5},
            headers=JSON_HEADERS, timeout=60,
        )
        assert r1.status_code == 200
        r2 = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "engineering", "limit": 5},
            headers=JSON_HEADERS, timeout=60,
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["skipped_duplicates"] >= 1, f"expected dedupes on 2nd call: {d2}"

    def test_remotive_jobs_appear_in_list(self):
        r = requests.get(f"{BASE_URL}/api/jobs?limit=200", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        jobs = r.json()["jobs"]
        remotive = [j for j in jobs if j.get("source") == "remotive"]
        assert len(remotive) >= 1, "no remotive jobs in list"
        sample = remotive[0]
        assert sample.get("source_url"), f"remotive job missing source_url: {sample}"


# ---------- Regression ----------
class TestRegression:
    def test_auth_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS, timeout=15)
        assert r.status_code == 200

    def test_jobs(self):
        r = requests.get(f"{BASE_URL}/api/jobs", headers=HEADERS, timeout=20)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_missions_today(self):
        r = requests.get(f"{BASE_URL}/api/missions/today", headers=HEADERS, timeout=60)
        assert r.status_code == 200

    def test_billing_me(self):
        r = requests.get(f"{BASE_URL}/api/billing/me", headers=HEADERS, timeout=15)
        assert r.status_code == 200

    def test_billing_checkout(self):
        r = requests.post(
            f"{BASE_URL}/api/billing/checkout",
            json={"plan_id": "pro", "origin_url": "https://example.com"},
            headers=JSON_HEADERS, timeout=30,
        )
        assert r.status_code == 200
        assert "url" in r.json()


@pytest.fixture(scope="session", autouse=True)
def _final_cleanup():
    yield
    # Leave user on free plan to keep state clean
    _set_plan_free()
    _reset_quota()
