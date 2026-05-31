"""Pytest bootstrap for CI and local backend integration tests."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── sys.path bootstrap ────────────────────────────────────────────
# Tests run from the repo root (pytest backend/tests/) so backend/
# must be on sys.path for local module imports to resolve.
_backend_dir = str(Path(__file__).parent.parent.resolve())
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from pymongo import MongoClient  # noqa: E402

# Default to the local backend started by CI
os.environ.setdefault("REACT_APP_BACKEND_URL", "http://localhost:8001")
os.environ.setdefault("TEST_SESSION_TOKEN", "test_session_career_os")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "career_os")


def _seed_test_identity() -> None:
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    token = os.environ["TEST_SESSION_TOKEN"]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)

    client = MongoClient(mongo_url)
    db = client[db_name]

    db.users.update_one(
        {"user_id": "user_testseed01"},
        {
            "$set": {
                "user_id": "user_testseed01",
                "email": "test.career@example.com",
                "name": "Test Career",
                "picture": "https://example.com/avatar.png",
                "auth_provider": "google",
                "xp": 0,
                "level": 1,
                "streak": 0,
                "last_active_date": None,
                "plan": "free",
                "created_at": now,
            }
        },
        upsert=True,
    )

    db.user_sessions.update_one(
        {"session_token": token},
        {
            "$set": {
                "session_token": token,
                "user_id": "user_testseed01",
                "created_at": now,
                "expires_at": expires_at,
            }
        },
        upsert=True,
    )


def _seed_test_jobs() -> None:
    """Seed mock jobs for test_list_jobs to pass."""
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    
    # Mock jobs data (simplified)
    mock_jobs = [
        {
            "title": f"Software Engineer {i}",
            "company": f"Company {i}",
            "location": "Remote",
            "job_id": f"job_{i:04d}",
            "source": "test",
        }
        for i in range(10)
    ]
    
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    # Only seed if jobs collection is empty
    if db.jobs.count_documents({}) == 0:
        db.jobs.insert_many(mock_jobs)


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    _seed_test_identity()
    _seed_test_jobs()
