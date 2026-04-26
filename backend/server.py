"""Main FastAPI server for AI Career OS."""
from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import router as auth_router, get_current_user
from routes_jobs import router as jobs_router
from routes_emails import router as emails_router
from routes_gamification import router as gam_router
from routes_insights import router as insights_router
from routes_profile import router as profile_router
from seed import seed_jobs_if_empty, seed_user_emails, seed_user_profile

app = FastAPI(title="AI Career OS")

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(emails_router)
app.include_router(gam_router)
app.include_router(insights_router)
app.include_router(profile_router)


@app.get("/api/")
async def root():
    return {"name": "AI Career OS", "status": "ok"}


@app.post("/api/seed-me")
async def seed_for_user(user=Depends(get_current_user)):
    """Seed mock emails + sample profile for a new user."""
    await seed_user_emails(user["user_id"])
    await seed_user_profile(user["user_id"])
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    await seed_jobs_if_empty()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
