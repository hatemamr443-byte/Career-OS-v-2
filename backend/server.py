"""Main FastAPI server for AI Career OS."""
# ruff: noqa: E402  — load_dotenv() must run before local module imports

# ── STEP 1: stdlib only (no env vars needed) ───────────────────────
import logging
from pathlib import Path
import uuid as _uuid

# ── STEP 2: Load .env BEFORE any project module imports ────────────
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ── STEP 3: Configure logging (reads LOG_LEVEL from env) ───────────
from logging_config import configure_logging
configure_logging()

# ── STEP 4: Now safe to import all project modules ─────────────────
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

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
from routes_memory import router as memory_router
from routes_extension import router as extension_router
from routes_profile import router as profile_router
from routes_salary import router as salary_router
from seed import seed_user_emails, seed_user_profile

# ── Environment Validation (fail-fast on startup) ───────────────────
def _validate_environment() -> None:
    """Verify critical environment variables. Fail hard if missing."""
    logger = logging.getLogger(__name__)
    errors: list[str] = []

    if not _cfg.MONGO_URL:
        errors.append("MONGO_URL is required")
    if not _cfg.DB_NAME:
        errors.append("DB_NAME is required")

    # Production-only strict checks
    if _cfg.ENVIRONMENT in ("production", "staging"):
        if _cfg.CORS_ORIGINS == "*":
            logger.warning("⚠️  CORS_ORIGINS='*' is insecure in %s!", _cfg.ENVIRONMENT)
        if not _cfg.STRIPE_SECRET_KEY:
            logger.warning("⚠️  STRIPE_SECRET_KEY not set — billing disabled")
        if not _cfg.STRIPE_WEBHOOK_SECRET:
            logger.warning("⚠️  STRIPE_WEBHOOK_SECRET not set — webhooks will reject all events")
        if not _cfg.ADMIN_TOKEN:
            errors.append("ADMIN_TOKEN is required in production")
        if not _cfg.CRON_TOKEN:
            errors.append("CRON_TOKEN is required in production")

    if errors:
        for e in errors:
            logger.critical("❌ Config error: %s", e)
        raise RuntimeError(f"Startup failed — missing config: {', '.join(errors)}")

    llm_count = sum([
        bool(_cfg.EMERGENT_LLM_KEY),
        bool(_cfg.ANTHROPIC_API_KEY),
        bool(_cfg.OPENAI_API_KEY),
        bool(_cfg.GEMINI_API_KEY),
    ])
    logger.info(
        "✅ Environment validation passed | env=%s | llm_providers=%d",
        _cfg.ENVIRONMENT, llm_count,
    )

from config import settings as _cfg  # noqa: E402

# Validate environment on module load
_validate_environment()

# ── Sentry Error Monitoring ──────────────────────────────────────
_sentry_dsn = _cfg.SENTRY_DSN
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
            environment=_cfg.ENVIRONMENT,
            release=_cfg.RENDER_GIT_COMMIT or "unknown",
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
app.include_router(memory_router)
app.include_router(extension_router)


@app.get("/health")
async def health():
    """Liveness + basic DB check. Returns 200 if alive.
    Also checks DB so existing tests (test_iter6) that assert db=connected pass.
    """
    from datetime import datetime, timezone
    from db import db as mongo_db

    try:
        await mongo_db.command("ping")
        db_status = "connected"
    except Exception as ex:
        db_status = f"error: {ex}"

    return {
        "status": "ok",
        "version": "2.1.0",
        "db": db_status,
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
    """Startup hook - initialize database and indexes."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from db import init_db
        await init_db()
        logger.info("✅ Database initialized with indexes")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization warning: {e}")
    
    logger.info("✅ Application started")


@app.on_event("shutdown")
async def on_shutdown():
    """Graceful shutdown — close MongoDB connection."""
    try:
        from db import db as mongo_db
        mongo_db.client.close()  # close() returns None, not a coroutine
        logging.getLogger(__name__).info("MongoDB connection closed ✓")
    except Exception as ex:
        logging.getLogger(__name__).warning("Shutdown error: %s", ex)


# ── Drip email cron ───────────────────────────────────────────────
@app.post("/api/cron/welcome-emails")
async def cron_welcome_emails(request: Request):
    """Daily cron — sends day1/day3/day7 drip emails. Secured by CRON_TOKEN."""
    token = request.headers.get("x-cron-token", "")
    if token != _cfg.CRON_TOKEN:
        from fastapi import HTTPException

        raise HTTPException(401, "Unauthorized")
    from welcome_emails import run_drip_sequence

    return await run_drip_sequence()


@app.post("/api/internal/consolidate-memory")
async def consolidate_memory_endpoint(request: Request):
    """Daily cron — consolidates career events into AI notes."""
    if request.headers.get("x-cron-token","") != _cfg.CRON_TOKEN:
        from fastapi import HTTPException
        raise HTTPException(401, "Unauthorized")
    from fastapi.background import BackgroundTasks
    from memory_consolidation import run_consolidation_batch
    bg = BackgroundTasks()
    bg.add_task(run_consolidation_batch)
    return {"ok": True, "message": "Memory consolidation running in background"}


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


# Request correlation ID for distributed tracing
class _RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        req_id = request.headers.get('x-request-id') or _uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers['x-request-id'] = req_id
        return response

app.add_middleware(_RequestIDMiddleware)

# ── Global exception handler (FastAPI built-in, not BaseHTTPMiddleware) ──

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import logging
    logging.getLogger(__name__).error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "status": 500},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "detail": str(exc), "status": 400},
    )

# Parse CORS origins from comma-separated string
_cors_origins = [o.strip() for o in _cfg.CORS_ORIGINS.split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["*"]

# SECURITY: credentials=True requires specific origins, not "*"
# When CORS_ORIGINS="*" (dev mode), disable credentials to avoid browser rejection
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_allow_credentials,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Cron-Token", "Stripe-Signature"],
)
