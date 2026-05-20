"""MongoDB connection and collection accessors."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]

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
