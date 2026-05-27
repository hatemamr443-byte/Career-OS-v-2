"""MongoDB connection and collection accessors."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# CRITICAL: Fail-fast if MongoDB connection not configured
_mongo_url = os.environ.get("MONGO_URL")
_db_name   = os.environ.get("DB_NAME")

if not _mongo_url:
    raise RuntimeError(
        "❌ FATAL: MONGO_URL environment variable not set.\n"
        "Career OS requires explicit MongoDB connection configuration.\n"
        "Set MONGO_URL to your MongoDB Atlas connection string or local MongoDB URI."
    )

if not _db_name:
    raise RuntimeError(
        "❌ FATAL: DB_NAME environment variable not set.\n"
        "Set DB_NAME to your database name (e.g., 'career_os')."
    )

_client = AsyncIOMotorClient(_mongo_url)
db = _client[_db_name]

# Collections
users = db.users
sessions = db.user_sessions
jobs = db.jobs
applications = db.applications
emails = db.emails
missions = db.missions
coach_messages = db.coach_messages
decisions = db.decisions
profiles = db.profiles  # CV / identity graph
# P1 collections
activity_logs = db.activity_logs
notifications = db.notifications
xp_events = db.xp_events
onboarding = db.onboarding
bookmarks = db.bookmarks
# New feature collections
cv_versions        = db.cv_versions
interview_sessions = db.interview_sessions
emails_sent        = db.emails_sent
# Referrals + bookmarks + AI usage tracking
referrals          = db.referrals
ai_usage           = db.ai_usage
# Career Intelligence collections
career_graph   = db.career_graph
career_events  = db.career_events
salary_cache   = db.salary_cache
episodes           = db.episodes           # episodic memory
events_outbox      = db.events_outbox      # durable event outbox
ai_telemetry       = db.ai_telemetry       # AI call telemetry
user_sessions      = db.user_sessions      # auth sessions


async def init_indexes() -> None:
    """Create all MongoDB indexes in parallel. Called once at startup."""
    import asyncio
    await asyncio.gather(
        db.users.create_index("user_id", unique=True, sparse=True),
        db.user_sessions.create_index("session_token", unique=True),
        db.user_sessions.create_index("expires_at"),
        db.jobs.create_index([("user_id", 1), ("created_at", -1)]),
        db.jobs.create_index("content_hash", sparse=True),
        db.applications.create_index([("user_id", 1), ("status", 1)]),
        db.applications.create_index([("user_id", 1), ("created_at", -1)]),
        db.career_events.create_index([("user_id", 1), ("created_at", -1)]),
        db.career_events.create_index([("user_id", 1), ("event_type", 1)]),
        db.activity_logs.create_index([("user_id", 1), ("created_at", -1)]),
        db.career_graph.create_index("user_id", unique=True, sparse=True),
        db.episodes.create_index([("user_id", 1), ("created_at", -1)]),
        db.episodes.create_index([("user_id", 1), ("importance", -1)]),
        db.episodes.create_index([("user_id", 1), ("episode_type", 1)]),
        db.ai_telemetry.create_index([("user_id", 1), ("created_at", -1)]),
        db.ai_telemetry.create_index("feature"),
        db.events_outbox.create_index([("delivered", 1), ("created_at", 1)]),
        db.notifications.create_index([("user_id", 1), ("read", 1)]),
        db.missions.create_index([("user_id", 1), ("date", 1)], unique=True, sparse=True),
        db.cv_versions.create_index([("user_id", 1), ("created_at", -1)]),
        db.interview_sessions.create_index([("user_id", 1), ("created_at", -1)]),
        return_exceptions=True,
    )
