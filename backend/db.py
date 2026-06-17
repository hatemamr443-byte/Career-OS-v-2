"""MongoDB connection and collection accessors."""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

# Import config (handles environment variables centrally)
from config import settings

ROOT_DIR = Path(__file__).parent

# CRITICAL: Fail-fast if MongoDB connection not configured
if not settings.MONGO_URL:
    raise RuntimeError(
        "❌ FATAL: MONGO_URL environment variable not set.\n"
        "Career OS requires explicit MongoDB connection configuration.\n"
        "Set MONGO_URL to your MongoDB Atlas connection string or local MongoDB URI."
    )

if not settings.DB_NAME:
    raise RuntimeError(
        "❌ FATAL: DB_NAME environment variable not set.\n"
        "Set DB_NAME to your database name (e.g., 'career_os')."
    )

# Create client with connection pooling
_client = AsyncIOMotorClient(
    settings.MONGO_URL,
    maxPoolSize=50,
    minPoolSize=2,
    serverSelectionTimeoutMS=3000,   # Reduced: 3s (was 5s)
    connectTimeoutMS=5000,           # Reduced: 5s (was 10s)
    retryWrites=True,
)

db = _client[settings.DB_NAME]

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
user_matches = db.user_matches  # Job match scores
billing = db.billing  # Subscription & payment records
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
        # Users
        db.users.create_index("user_id", unique=True, sparse=True),
        db.users.create_index("email", unique=True, sparse=True),
        db.users.create_index("created_at"),
        # Sessions
        db.user_sessions.create_index("session_token", unique=True),
        db.user_sessions.create_index("expires_at", expireAfterSeconds=0),
        # Jobs — text index for search (replaces regex scans)
        db.jobs.create_index("job_id", unique=True, sparse=True),
        db.jobs.create_index([("title", "text"), ("description", "text"), ("company", "text")]),
        db.jobs.create_index("location"),
        db.jobs.create_index("source"),
        db.jobs.create_index("skills_required"),
        db.jobs.create_index("posted_date"),
        # Applications
        db.applications.create_index([("user_id", 1), ("job_id", 1)], unique=True, sparse=True),
        db.applications.create_index([("user_id", 1), ("status", 1)]),
        db.applications.create_index([("user_id", 1), ("created_at", -1)]),
        # User matches
        db.user_matches.create_index([("user_id", 1), ("job_id", 1)], unique=True, sparse=True),
        db.user_matches.create_index([("user_id", 1), ("full_score", -1)]),
        # Profiles
        db.profiles.create_index("user_id", unique=True, sparse=True),
        db.profiles.create_index("skills"),
        # Billing
        db.billing.create_index("user_id", unique=True, sparse=True),
        db.billing.create_index("stripe_subscription_id", sparse=True),
        # Activity & Memory
        db.activity_logs.create_index([("user_id", 1), ("created_at", -1)]),
        db.career_events.create_index([("user_id", 1), ("created_at", -1)]),
        db.episodes.create_index([("user_id", 1), ("importance", -1)]),
        db.missions.create_index([("user_id", 1), ("date", 1)], unique=True, sparse=True),
        db.notifications.create_index([("user_id", 1), ("read", 1)]),
        db.events_outbox.create_index([("delivered", 1), ("created_at", 1)]),
        db.cv_versions.create_index([("user_id", 1), ("created_at", -1)]),
        return_exceptions=True,
    )


async def init_db() -> None:
    """Initialize database indexes. Called once at server startup."""
    try:
        await init_indexes()
        logging.getLogger(__name__).info("✅ Database indexes initialized")
    except Exception as e:
        logging.getLogger(__name__).warning("⚠️ Index init warning: %s", e)
