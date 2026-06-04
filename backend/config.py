"""Career OS — Production Configuration System

This module defines all environment variables and settings as a single
source of truth. Use `from config import settings` everywhere.

CRITICAL RULES:
- All env vars must be defined here
- Fail-fast if REQUIRED vars are missing
- Never use os.environ.get() directly in routes (use settings)
- All defaults are explicit and documented
"""

from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings

# ── Path Resolution ──────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """All Career OS environment configuration."""

    # ── REQUIRED: Database ───────────────────────────────────
    MONGO_URL: str = Field(..., description="MongoDB Atlas or local connection string")
    DB_NAME: str = Field(..., description="Database name")

    # ── REQUIRED: CORS ────────────────────────────────────────
    CORS_ORIGINS: str = Field(
        default="*",
        description="Comma-separated CORS allowed origins (use exact URL in prod)",
    )

    # ── REQUIRED: Security ───────────────────────────────────────
    CRON_TOKEN: str = Field(
        default="",
        description="Secret token for cron/scheduled job authentication",
    )
    ADMIN_TOKEN: str = Field(
        default="",
        description="Secret token for /admin/* endpoints (empty = disabled)",
    )

    # ── OPTIONAL: AI Providers ───────────────────────────────────
    # Emergent is recommended (single key for Claude/Gemini/GPT)
    EMERGENT_LLM_KEY: Optional[str] = Field(
        default=None,
        description="Emergent universal LLM key (Claude Sonnet + Gemini Flash + GPT)",
    )

    # Fallback providers (used if Emergent unavailable)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Claude API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")

    # ── OPTIONAL: Email ──────────────────────────────────────────
    RESEND_API_KEY: Optional[str] = Field(
        default=None,
        description="Resend email service API key",
    )
    EMAIL_FROM: str = Field(
        default="Career OS <noreply@career-os.io>",
        description="From address for all emails",
    )
    SENDER_EMAIL: Optional[str] = Field(
        default="onboarding@resend.dev",
        description="Sender email address (for backward compatibility)",
    )

    # ── OPTIONAL: Payments (Stripe) ─────────────────────────────
    STRIPE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Stripe secret API key (required for SaaS mode)",
    )
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        description="Stripe webhook signing secret",
    )
    STRIPE_PRICE_ID_BASIC: Optional[str] = Field(
        default=None,
        description="Stripe Price ID for Basic plan",
    )

    # ── OPTIONAL: External APIs ─────────────────────────────────
    FIRECRAWL_API_KEY: Optional[str] = Field(
        default=None,
        description="FireCrawl API key for web scraping",
    )
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Google OAuth Client ID for Gmail integration",
    )
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Google OAuth Client Secret",
    )
    GOOGLE_REDIRECT_URI: Optional[str] = Field(
        default=None,
        description="Google OAuth redirect URI",
    )
    DASHBOARD_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend dashboard URL for OAuth redirects",
    )
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse public key for LLM tracing",
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse secret key",
    )
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse API host",
    )
    ADZUNA_APP_ID: Optional[str] = Field(
        default=None,
        description="Adzuna job search API app ID",
    )
    ADZUNA_API_KEY: Optional[str] = Field(
        default=None,
        description="Adzuna job search API key",
    )
    JOOBLE_API_KEY: Optional[str] = Field(
        default=None,
        description="Jooble job search API key",
    )
    STRIPE_PRICE_ID_PRO: Optional[str] = Field(
        default=None,
        description="Stripe Price ID for Pro plan",
    )
    STRIPE_PRICE_ID_ENTERPRISE: Optional[str] = Field(
        default=None,
        description="Stripe Price ID for Enterprise plan",
    )

    # ── OPTIONAL: Error Monitoring ──────────────────────────────
    SENTRY_DSN: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking (if not set, Sentry disabled)",
    )

    # ── OPTIONAL: External APIs ─────────────────────────────────
    FIRECRAWL_API_KEY: Optional[str] = Field(
        default=None,
        description="Firecrawl web intelligence API",
    )

    # ── DEPLOYMENT ───────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment: development, staging, production",
    )
    RENDER_GIT_COMMIT: Optional[str] = Field(
        default=None,
        description="Git commit SHA (set by Render)",
    )

    class Config:
        env_file = _BACKEND_DIR / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without validation error

    def validate_required(self) -> None:
        """Fail-fast validation for required variables. Called at startup."""
        required = ["MONGO_URL", "DB_NAME"]
        missing = [var for var in required if not getattr(self, var, None)]

        if missing:
            raise ValueError(
                f"❌ STARTUP FAILED: Missing required environment variables: {', '.join(missing)}"
            )

    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# ── Singleton Settings Instance ──────────────────────────────────
# Loaded once at startup, used everywhere via: from config import settings
try:
    settings = Settings()
    settings.validate_required()
except ValueError as e:
    raise RuntimeError(str(e))
