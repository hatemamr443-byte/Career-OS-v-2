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

## Test Results (iteration 3)
- Backend: **19/19 passing** (100%)
- Frontend: **9/9 critical flows passing** (100%)
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
