"""Iteration 4: multi-source job ingest (Adzuna ES+GB, Jooble, Remotive) with dedupe."""
import os
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://job-agent-ai-6.preview.emergentagent.com").rstrip("/")
TOKEN = os.environ.get("TEST_SESSION_TOKEN", "test_session_career_os")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
JSON_HEADERS = {**HEADERS, "Content-Type": "application/json"}
USER_ID = "user_testseed01"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]


# ---------- Multi-source ingest (default mode) ----------
class TestMultiSourceIngest:
    def test_default_ingest_returns_breakdown_shape(self):
        r = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "python", "limit": 5},
            headers=JSON_HEADERS,
            timeout=120,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # Top-level shape
        for k in ["total_inserted", "by_source", "errors"]:
            assert k in d, f"missing key {k} in {d}"
        assert isinstance(d["total_inserted"], int)
        assert isinstance(d["by_source"], dict)
        assert isinstance(d["errors"], dict)

        # by_source MUST contain configured sources: adzuna_es, adzuna_gb, jooble, remotive
        expected_sources = {"adzuna_es", "adzuna_gb", "jooble", "remotive"}
        present = set(d["by_source"].keys()) | set(d["errors"].keys())
        missing = expected_sources - present
        assert not missing, f"missing sources from response: {missing}; got by_source={list(d['by_source'])} errors={list(d['errors'])}"

        # each source in by_source has {fetched, inserted}
        for src, stats in d["by_source"].items():
            assert "fetched" in stats, f"{src} missing 'fetched': {stats}"
            assert "inserted" in stats, f"{src} missing 'inserted': {stats}"
            assert isinstance(stats["fetched"], int)
            assert isinstance(stats["inserted"], int)
            assert stats["inserted"] <= stats["fetched"]

        # totals math
        total_inserted_calc = sum(s.get("inserted", 0) for s in d["by_source"].values())
        assert d["total_inserted"] == total_inserted_calc

    def test_dedupe_second_run_low_inserts(self):
        """Dedupe is verified by: (a) total inserts on 2nd call <= 1st call,
        and (b) NO duplicate content_hash rows in db. Live APIs may return
        slightly different results between calls so we don't strictly require 0."""
        r1 = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "python", "limit": 5},
            headers=JSON_HEADERS, timeout=120,
        )
        assert r1.status_code == 200
        d1 = r1.json()
        # Second run — same query — most should be dedupes
        r2 = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "python", "limit": 5},
            headers=JSON_HEADERS, timeout=120,
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["total_inserted"] <= d1["total_inserted"], (
            f"dedupe failed — 2nd run inserted more than 1st: {d1['total_inserted']} -> {d2['total_inserted']}"
        )
        # CRITICAL: no duplicate content_hash rows allowed
        pipeline = [
            {"$match": {"content_hash": {"$exists": True}}},
            {"$group": {"_id": "$content_hash", "n": {"$sum": 1}}},
            {"$match": {"n": {"$gt": 1}}},
        ]
        dupes = list(_db.jobs.aggregate(pipeline))
        assert not dupes, f"duplicate content_hash rows present: {dupes[:3]}"

    def test_legacy_remotive_mode(self):
        r = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"source": "remotive", "query": "python", "limit": 5},
            headers=JSON_HEADERS, timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["fetched", "inserted", "skipped_duplicates"]:
            assert k in d, f"missing key {k}: {d}"
        assert d["inserted"] + d["skipped_duplicates"] == d["fetched"]
        # legacy shape must NOT contain by_source
        assert "by_source" not in d


# ---------- Job listing + source field ----------
class TestJobsListing:
    def test_jobs_have_valid_source_field(self):
        r = requests.get(f"{BASE_URL}/api/jobs?limit=200", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        jobs = r.json()["jobs"]
        assert len(jobs) >= 1
        valid_sources = {"adzuna", "jooble", "remotive", "mock"}
        for j in jobs:
            assert j.get("source") in valid_sources, f"unexpected source: {j.get('source')} for {j.get('title')}"

    def test_adzuna_and_jooble_jobs_have_real_source_urls(self):
        # Only assert on real-source jobs (skip mock)
        r = requests.get(f"{BASE_URL}/api/jobs?limit=200", headers=HEADERS, timeout=30)
        jobs = r.json()["jobs"]
        for j in jobs:
            src = j.get("source")
            if src in ("adzuna", "jooble", "remotive"):
                url = j.get("source_url")
                assert url, f"{src} job missing source_url: {j.get('title')}"
                assert url.startswith("http"), f"bad source_url: {url}"

    def test_content_hash_persisted(self):
        # Inspect Mongo directly — only check real-source jobs from iter4+
        # (older mock/remotive seed data predates the content_hash field)
        sample = _db.jobs.find_one(
            {"source": {"$in": ["adzuna", "jooble"]}, "content_hash": {"$exists": True}}
        )
        assert sample is not None, "no adzuna/jooble jobs with content_hash in db"
        assert sample.get("content_hash"), f"content_hash missing on {sample.get('job_id')}"
        assert len(sample["content_hash"]) == 40  # sha1 hex
        # Verify majority of real-source jobs have it
        real_total = _db.jobs.count_documents({"source": {"$in": ["adzuna", "jooble"]}})
        real_with_hash = _db.jobs.count_documents(
            {"source": {"$in": ["adzuna", "jooble"]}, "content_hash": {"$exists": True}}
        )
        assert real_with_hash == real_total, (
            f"some adzuna/jooble jobs missing content_hash: {real_with_hash}/{real_total}"
        )

    def test_at_least_one_adzuna_job_present(self):
        """Adzuna ES or GB should have returned at least 1 job for query='python'."""
        r = requests.get(f"{BASE_URL}/api/jobs?limit=200", headers=HEADERS, timeout=30)
        jobs = r.json()["jobs"]
        adzuna = [j for j in jobs if j.get("source") == "adzuna"]
        assert len(adzuna) >= 1, "no adzuna jobs found — check ADZUNA_APP_ID/KEY env vars"


# ---------- Env config ----------
class TestEnvConfig:
    def test_adzuna_countries_env_is_es_gb(self):
        """Verify ADZUNA_COUNTRIES env is set to supported countries (NOT pt)."""
        # We can't read backend env directly, but we can confirm by_source keys reflect it
        r = requests.post(
            f"{BASE_URL}/api/jobs/ingest",
            json={"query": "developer", "limit": 3},
            headers=JSON_HEADERS, timeout=120,
        )
        assert r.status_code == 200
        d = r.json()
        present = set(d["by_source"].keys()) | set(d["errors"].keys())
        assert "adzuna_es" in present
        assert "adzuna_gb" in present
        # Adzuna pt is NOT a supported country and must NOT be configured
        assert "adzuna_pt" not in present, "adzuna_pt should NOT be in ADZUNA_COUNTRIES (unsupported)"


# ---------- Regression: existing endpoints ----------
class TestRegression:
    def test_me_usage_works(self):
        r = requests.get(f"{BASE_URL}/api/me/usage", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        assert "plan" in r.json()

    def test_billing_me_works(self):
        r = requests.get(f"{BASE_URL}/api/billing/me", headers=HEADERS, timeout=15)
        assert r.status_code == 200
        assert "plan" in r.json()

    def test_billing_cancel_idempotent(self):
        # Make sure plan is free first
        _db.users.update_one({"user_id": USER_ID}, {"$set": {"plan": "free"}, "$unset": {"plan_expires_at": ""}})
        r = requests.post(f"{BASE_URL}/api/billing/cancel", headers=JSON_HEADERS, timeout=15)
        assert r.status_code == 200
        assert r.json()["plan"] == "free"

    def test_profile_upload_cv_endpoint_reachable(self):
        # Just check that the endpoint exists & rejects non-pdf with 400 (not 404/500)
        files = {"file": ("not_pdf.txt", b"hello world", "text/plain")}
        r = requests.post(f"{BASE_URL}/api/profile/upload-cv", headers=HEADERS, files=files, timeout=30)
        assert r.status_code == 400, r.text
