# AI Career OS — PRD

## Original Problem Statement
Build a full-stack AI-powered career decision system. Not a job board — an AI agent that decides, recommends, tracks, and learns.

## User Choices
- **Auth**: Emergent Google OAuth + JWT-ready abstraction
- **LLM**: Claude Sonnet 4.5 (reasoning) + Gemini 3 Flash (fast/bulk)
- **DB**: MongoDB
- **Billing**: Stripe (Pro $19 / Team $49 / Free)
- **Job source**: Mock seed + Remotive real API (Phase 2: Playwright connectors)

## Implemented (through Jun 2026)
### v0.1 — Core MVP
- ✅ Emergent Google OAuth + AuthService abstraction
- ✅ AI Decision Engine (Claude) — score, decision, reasoning, strengths, gaps
- ✅ Application lifecycle tracker (6 states + timeline)
- ✅ Mock recruiter inbox with AI classification (Gemini Flash)
- ✅ Daily AI-generated missions + XP/streak/level + AI Coach (Claude with context)
- ✅ Insights: funnel, rates, rejection pattern detection
- ✅ Career Map kanban
- ✅ CV editor + Claude-powered text parsing

### v0.2 — SaaS readiness
- ✅ Marketing landing page at `/` + Pricing page at `/pricing`
- ✅ Stripe checkout (one-time monthly charge) — Pro $19 / Team $49
- ✅ Webhook handler — source of truth for plan activation
- ✅ Billing management page + sidebar nav

### v0.3 — Productization
- ✅ **Free-tier gating**: 5 AI matches/month for free; cached results don't count; Pro/Team unlimited
- ✅ **Usage banner** (`UsageBanner.jsx`) on Jobs/Insights/JobDetail/Billing — loss-aversion CTA
- ✅ **Quota-exceeded error panel** on JobDetail with direct Upgrade link
- ✅ **Subscription cancel/downgrade** — `/api/billing/cancel` + confirmation modal
- ✅ **PDF CV upload** — pypdf extraction + Claude parsing (5MB limit, image-only PDF guard)
- ✅ **Real job ingest** — `/api/jobs/ingest` pulls live remote jobs from Remotive public API, dedupes by `source_url`, auto-extracts skills + seniority
- ✅ **Render deployment guide** at `/app/RENDER_DEPLOY.md` + `.env.example` for both services

### v0.4 — Multi-source job ingest (real production APIs)
- ✅ **Adzuna connector** (`fetch_adzuna(country)`) — primary source. Configurable countries via `ADZUNA_COUNTRIES` env (default `es,gb`). Portugal not supported by Adzuna; Spain proxies Iberian market.
- ✅ **Jooble connector** (`fetch_jooble(query, location)`) — secondary. Location configurable via `JOOBLE_LOCATION` env (default `Lisbon`).
- ✅ **Remotive** kept as tertiary (remote-only).
- ✅ `POST /api/jobs/ingest` now runs all 3 sources in priority order, returns per-source breakdown + errors. Legacy `{source:"remotive"}` flag preserves old behavior.
- ✅ **Content-hash dedupe**: SHA1(title|company|location|source_url) — race-proof via MongoDB unique partial index `content_hash_unique`.
- ✅ Unique indexes on startup: `jobs.content_hash`, `match_usage.user_id+month`, `payment_transactions.session_id`.
- ✅ Frontend: ingest breakdown panel shows per-source counts, source badges on all real-job cards.

### v0.5 — Daily digest emails + true parallel ingest
- ✅ **`profile.daily_matches` toggle** + Profile-page UI card with switch + "Send test now" button
- ✅ **Resend integration** (`emailer.py`) — `send_email()` with graceful no-op when `RESEND_API_KEY` blank; `render_daily_digest()` pure function returns (html, text)
- ✅ **Daily digest pipeline** (`daily_digest.py`) — pulls top 3 unique jobs per user, 20-hour gate to prevent duplicates, excludes already-applied/decided jobs, real Resend send via `asyncio.to_thread`
- ✅ **Cron endpoint** `POST /api/internal/run-daily-digest` with `X-Cron-Token` header auth — external cron (cron-job.org) hits this daily
- ✅ **True parallel ingest** — `asyncio.gather()` over Adzuna×N + Jooble + Remotive. Measured: **0.6–0.8s** (was 5s sequential, 80s worst case)
- ✅ Added `RESEND_API_KEY`, `SENDER_EMAIL`, `CRON_TOKEN`, `ADZUNA_COUNTRIES`, `JOOBLE_LOCATION` to `.env.example` and Render deploy guide

## Test Results (iteration 5)
- Backend: **13/13 passing** (100%) on iter5 notifications + parallel ingest
- Frontend: **6/6 UI flows passing** (100%)
- Parallel ingest verified at **0.6s** end-to-end after asyncio.gather rewrite
- Known carryover (NOT a regression): `/api/billing/status` returns DB-cached state because Emergent Stripe proxy doesn't support `retrieve`. Webhook is source of truth.

## Backlog (P1 / P2)
- P1: Plan-aware feature gating beyond match limit (e.g., AI Coach memory only for Pro)
- P1: Strategy Switching Engine — auto-pivot when interview rate drops
- P1: Decision Replay — log predictions vs outcomes, fine-tune ranking over time
- P2: Playwright connectors for Indeed/LinkedIn (Remotive covers remote jobs; geo-specific roles need scrapers)
- P2: Gmail OAuth ingestion (data contracts already Gmail-shaped)
- P2: Embeddings-based vector match (currently skill-overlap + Claude reasoning)
- P2: Email digest via Resend
- P2: GDPR data export/delete

## Test Credentials
See `/app/memory/test_credentials.md` — Bearer `test_session_career_os` (user_testseed01).

## Deployment
- ✅ Native Emergent: ready (`deployment_agent` PASS in iteration 1)
- ✅ Render: complete guide at `/app/RENDER_DEPLOY.md` — note OAuth host caveat
