"""MongoDB connection and collection accessors."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

_mongo_url = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
_db_name   = os.environ.get("DB_NAME") or "career_os"
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
    """Create all MongoDB indexes. Called once at startup."""
    # Users
    await db.users.create_index("user_id", unique=True, sparse=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("expires_at")
    # Jobs + Applications
    await db.jobs.create_index([("user_id", 1), ("created_at", -1)])
    await db.jobs.create_index("content_hash", sparse=True)
    await db.applications.create_index([("user_id", 1), ("status", 1)])
    await db.applications.create_index([("user_id", 1), ("created_at", -1)])
    # Intelligence
    await db.career_events.create_index([("user_id", 1), ("created_at", -1)])
    await db.career_events.create_index([("user_id", 1), ("event_type", 1)])
    await db.activity_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.career_graph.create_index("user_id", unique=True, sparse=True)
    # Episodic memory
    await db.episodes.create_index([("user_id", 1), ("created_at", -1)])
    await db.episodes.create_index([("user_id", 1), ("importance", -1)])
    await db.episodes.create_index([("user_id", 1), ("episode_type", 1)])
    # Telemetry + outbox
    await db.ai_telemetry.create_index([("user_id", 1), ("created_at", -1)])
    await db.ai_telemetry.create_index("feature")
    await db.events_outbox.create_index([("delivered", 1), ("created_at", 1)])
    # Notifications + gamification
    await db.notifications.create_index([("user_id", 1), ("read", 1)])
    await db.missions.create_index([("user_id", 1), ("date", 1)], unique=True, sparse=True)
    await db.cv_versions.create_index([("user_id", 1), ("created_at", -1)])
    await db.interview_sessions.create_index([("user_id", 1), ("created_at", -1)])
