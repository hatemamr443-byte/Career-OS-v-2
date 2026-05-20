"""Pytest bootstrap for local backend integration tests."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

# Use the local backend by default so tests validate the repo itself.
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


def pytest_sessionstart(session):  # noqa: ARG001
    _seed_test_identity()
