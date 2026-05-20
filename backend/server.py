"""Main FastAPI server for AI Career OS."""
import logging
import os
from logging_config import configure_logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from auth import get_current_user, router as auth_router
from routes_activity import router as activity_router
from routes_billing import router as billing_router, webhook_router as billing_webhook
from routes_cv import router as cv_router
from routes_cv_intel import router as cv_intel_router
from routes_decision import router as decision_router
from routes_emails import router as emails_router
from routes_gamification import router as gam_router
from routes_gdpr import router as gdpr_router
from routes_gmail import router as gmail_router
from routes_insights import router as insights_router
from routes_interview import router as interview_router
from routes_jobs import router as jobs_router
from routes_notifications import router as notifications_router
from routes_onboarding import router as onboarding_router
from routes_orchestrator import router as orchestrator_router
from routes_admin import router as admin_router
from routes_profile import router as profile_router
from routes_salary import router as salary_router
from seed import seed_jobs_if_empty, seed_user_emails, seed_user_profile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ── Sentry Error Monitoring ──────────────────────────────────────
_sentry_dsn = os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.environ.get("ENVIRONMENT", "production"),
            release=os.environ.get("RENDER_GIT_COMMIT", "unknown"),
        )
        logging.getLogger(__name__).info("Sentry initialized ✓")
    except ImportError:
        logging.getLogger(__name__).warning("sentry-sdk not installed — skipping")

app = FastAPI(
    title="Career OS — AI Career Intelligence System",
    description="Persistent AI career operating system: job matching, CV tailoring, interview prep, salary intelligence.",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(emails_router)
app.include_router(gam_router)
app.include_router(insights_router)
app.include_router(profile_router)
app.include_router(billing_router)
app.include_router(billing_webhook)
app.include_router(notifications_router)
app.include_router(activity_router)
app.include_router(onboarding_router)
app.include_router(gmail_router)
app.include_router(cv_intel_router)
app.include_router(cv_router)
app.include_router(interview_router)
app.include_router(salary_router)
app.include_router(gdpr_router)
app.include_router(decision_router)
app.include_router(orchestrator_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    """Liveness probe — Render health check. Returns 200 if process is alive."""
    from datetime import datetime, timezone

    return {
        "status": "ok",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/ready")
async def health_ready():
    """Readiness probe — checks DB + LLM availability before accepting traffic."""
    from datetime import datetime, timezone

    from db import db as mongo_db
    from llm_service import llm_health_check

    issues = []

    # DB check
    try:
        await mongo_db.command("ping")
        db_status = "connected"
    except Exception as ex:
        db_status = f"error: {ex}"
        issues.append(f"db: {ex}")

    # LLM check (non-blocking — degraded but still ready)
    try:
        llm_status = await llm_health_check()
    except Exception as ex:
        llm_status = {"error": str(ex)}

    ready = db_status == "connected"  # DB is the hard dependency
    return {
        "ready": ready,
        "status": "ready" if ready else "degraded",
        "version": "2.1.0",
        "db": db_status,
        "llm": llm_status,
        "issues": issues,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/")
async def root():
    return {"name": "AI Career OS", "version": "2.1.0", "status": "ok"}


@app.post("/api/seed-me")
async def seed_for_user(user=Depends(get_current_user)):
    """Seed mock emails + sample profile for a new user."""
    await seed_user_emails(user["user_id"])
    await seed_user_profile(user["user_id"])
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    await seed_jobs_if_empty()
    # Ensure dedupe race-safety on jobs.content_hash (partial index — only docs that have the field)
    try:
        from db import db as mongo_db, jobs as jobs_col

        await jobs_col.create_index(
            "content_hash",
            unique=True,
            partialFilterExpression={"content_hash": {"$exists": True}},
            name="content_hash_unique",
        )
        await mongo_db.match_usage.create_index([("user_id", 1), ("month", 1)], unique=True, name="usage_uq")
        await mongo_db.payment_transactions.create_index("session_id", unique=True, name="session_uq")
        # P1 indexes
        await mongo_db.activity_logs.create_index([("user_id", 1), ("created_at", -1)], name="activity_user_time")
        await mongo_db.notifications.create_index([("user_id", 1), ("read", 1), ("created_at", -1)], name="notif_user_unread")
        await mongo_db.xp_events.create_index([("user_id", 1), ("created_at", -1)], name="xp_user_time")
        await mongo_db.bookmarks.create_index([("user_id", 1), ("job_id", 1)], unique=True, name="bookmark_uq")
        await mongo_db.cv_versions.create_index([("user_id", 1), ("created_at", -1)], name="cv_ver_user_time")
        await mongo_db.interview_sessions.create_index([("user_id", 1), ("created_at", -1)], name="iv_session_user_time")
        await mongo_db.ai_usage.create_index([("user_id", 1), ("feature", 1), ("date", 1)], unique=True, name="ai_usage_uq")
        await mongo_db.referrals.create_index("code", unique=True, name="referral_code_uq")
        await mongo_db.emails_sent.create_index([("user_id", 1), ("sequence_key", 1)], unique=True, name="emails_sent_uq")
        # Career Intelligence indexes
        await mongo_db.career_graph.create_index("user_id", unique=True, name="career_graph_user_uq")
        await mongo_db.career_events.create_index([("user_id", 1), ("created_at", -1)], name="career_events_user_time")
        await mongo_db.career_events.create_index(
            [("user_id", 1), ("event_type", 1), ("created_at", -1)],
            name="career_events_user_type_time",
        )
        # Orchestration / observability indexes
        await mongo_db.ai_telemetry.create_index([("user_id", 1), ("created_at", -1)], name="ai_telemetry_user_time")
        await mongo_db.ai_telemetry.create_index([("feature", 1), ("created_at", -1)], name="ai_telemetry_feature_time")
        await mongo_db.events_outbox.create_index([("delivered", 1), ("created_at", 1)], name="outbox_delivery")
        # P1 workflow handoff stores
        await mongo_db.workflow_hints.create_index([("user_id", 1), ("kind", 1)], unique=True, name="wf_hints_uq")
        await mongo_db.interview_prep_context.create_index([("user_id", 1), ("from_addr", 1)], unique=True, name="ipc_uq")
        await mongo_db.cv_tailor_hints.create_index([("user_id", 1), ("job_id", 1)], unique=True, name="cv_hints_uq")
        await mongo_db.salary_comparison.create_index([("user_id", 1), ("company", 1)], unique=True, name="salary_cmp_uq")
        await mongo_db.insight_dismissals.create_index([("user_id", 1), ("insight_id", 1)], unique=True, name="insight_dismiss_uq")
        await mongo_db.salary_cache.create_index([("user_id", 1), ("role", 1), ("location", 1)], name="salary_cache_uq")
    except Exception as ex:
        logging.warning("Index creation skipped: %s", ex)

    # Wire orchestrator subscribers (idempotent)
    try:
        from orchestrator import wire_subscribers

        wire_subscribers()
    except Exception as ex:
        logging.warning("Subscriber wiring failed: %s", ex)


# ── Drip email cron ───────────────────────────────────────────────
@app.post("/api/cron/welcome-emails")
async def cron_welcome_emails(request: Request):
    """Daily cron — sends day1/day3/day7 drip emails. Secured by CRON_TOKEN."""
    token = request.headers.get("x-cron-token", "")
    if token != os.environ.get("CRON_TOKEN", ""):
        from fastapi import HTTPException

        raise HTTPException(401, "Unauthorized")
    from welcome_emails import run_drip_sequence

    return await run_drip_sequence()


@app.get("/api/billing/ai-usage")
async def ai_usage_route(user=Depends(get_current_user)):
    """Expose AI usage summary for the frontend."""
    from ai_limits import get_ai_usage_summary
    from quota import get_effective_plan

    plan = await get_effective_plan(user)
    if user.get("trial_active"):
        plan = "pro"
    summary = await get_ai_usage_summary(user["user_id"], plan)
    return {"plan": plan, "usage": summary}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_logging()  # structured JSON in prod, coloured dev format locally
