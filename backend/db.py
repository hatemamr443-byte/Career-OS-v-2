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
