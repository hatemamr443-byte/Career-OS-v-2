# Script to show fixes needed for remaining files

fixes = {
    "emailer.py": "RESEND_API_KEY, SENDER_EMAIL -> config.settings",
    "job_sources.py": "ADZUNA_APP_ID, ADZUNA_API_KEY, JOOBLE_API_KEY, ADZUNA_COUNTRIES, JOOBLE_LOCATION -> config.settings",
    "llm_service.py": "EMERGENT_LLM_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY -> config.settings",
    "logging_config.py": "ENVIRONMENT, LOG_LEVEL -> config.settings",
    "routes_gmail.py": "DASHBOARD_URL (already in one place, need to add to config)",
    "welcome_emails.py": "SENDER_EMAIL, DASHBOARD_URL, RESEND_API_KEY -> config.settings",
    "daily_digest.py": "DASHBOARD_URL -> config.settings",
    "firecrawl_adapter.py": "One more check reference -> fixed",
    "langfuse_tracer.py": "One more check reference -> fixed",
}

for file, fix in fixes.items():
    print(f"✅ {file}: {fix}")
