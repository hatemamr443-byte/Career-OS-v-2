"""MongoDB connection and collection accessors."""
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
    maxPoolSize=50,  # Maximum 50 connections
    minPoolSize=10,  # Minimum 10 connections
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
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


# ── Index Creation for Performance ──────────────────────────
async def _ensure_indexes() -> None:
    """Create indexes for frequently queried collections.
    
    Indexes significantly improve query performance on large datasets.
    Called once at server startup.
    """
    try:
        # Users collection indexes
        await users.create_index("email", unique=True)
        await users.create_index("user_id", unique=True)
        await users.create_index("created_at")
        
        # Profiles collection indexes
        await profiles.create_index("user_id", unique=True)
        await profiles.create_index("skills")  # For skill-based queries
        
        # Jobs collection indexes
        await jobs.create_index("job_id", unique=True)
        await jobs.create_index("title")
        await jobs.create_index("company")
        await jobs.create_index("location")
        await jobs.create_index("skills_required")
        await jobs.create_index("source")
        await jobs.create_index("posted_date", expireAfterSeconds=86400*30)  # Auto-delete after 30 days
        
        # Applications collection indexes
        await applications.create_index([("user_id", 1), ("job_id", 1)], unique=True)
        await applications.create_index("user_id")
        await applications.create_index("job_id")
        await applications.create_index("status")
        await applications.create_index("applied_at")
        
        # User matches indexes
        await user_matches.create_index([("user_id", 1), ("job_id", 1)], unique=True)
        await user_matches.create_index("user_id")
        await user_matches.create_index("full_score", direction=-1)  # For sorting
        
        # Billing collection indexes
        await billing.create_index("user_id", unique=True)
        await billing.create_index("stripe_subscription_id")
        await billing.create_index("status")
        
        print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not create indexes: {e}")


# Call this function in server startup
async def init_db() -> None:
    """Initialize database connections and indexes."""
    await _ensure_indexes()
