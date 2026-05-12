# AI Career OS — PRD

## Original Problem Statement
Build a full-stack AI-powered platform that acts as a personal career assistant and decision-making system. Not a job board — a decision-driven AI system that decides, recommends, tracks, and improves the user's job search strategy.

## User Choices (Feb 2026)
- **Auth**: Emergent Google OAuth + JWT-ready abstraction
- **LLM**: Multi-model router — Claude Sonnet 4.5 (reasoning), Gemini 3 Flash (fast/bulk)
- **Jobs**: Hybrid — mock dataset + manual entry, pluggable JobSource
- **DB**: MongoDB (vector matching abstracted for future Pinecone/Postgres)
- **Email**: Mock inbox with full AI pipeline
- **Billing**: Stripe via Emergent proxy (sk_test_emergent) — Pro $19 / Team $49 / Free

## Implemented (through May 2026)
- ✅ All v0.1 MVP features (Decision Engine, Lifecycle, Email AI, Missions, XP/Streak, Coach, Insights, Career Map, Profile)
- ✅ Marketing landing page at `/` (logged-out) with hero + features + flow + CTA
- ✅ Pricing page at `/pricing` (public) with 3 tiers
- ✅ Stripe checkout integration via emergentintegrations
- ✅ `payment_transactions` collection with idempotent plan activation
- ✅ Webhook handler at `/api/webhook/stripe` (source of truth for plan activation)
- ✅ Polling endpoint `/api/billing/status/{session_id}` with graceful fallback to DB state (Emergent Stripe proxy doesn't support `retrieve`)
- ✅ Billing management page at `/billing` (logged-in) + sidebar nav
- ✅ User model extended with `plan` and `plan_expires_at` fields

## Backlog (P0 / P1 / P2)
- P1: Real job source connectors (Indeed/LinkedIn via Playwright)
- P1: Gmail OAuth ingestion (data contracts already match Gmail schema)
- P1: Plan-gating — enforce free tier limit of 5 AI matches/month (currently unlimited)
- P1: Customer portal — let users cancel subscription from the Billing page
- P1: Strategy Switching Engine — auto-detect low conversion + suggest pivots
- P1: Decision Replay system — record outcomes vs predictions, learn over time
- P2: Embeddings-based vector search (currently skill-overlap heuristic)
- P2: Email digest via Resend (weekly summary)
- P2: PDF CV upload (currently text paste only)
- P2: GDPR data export + deletion endpoint

## Known Limitations
- **Stripe `retrieve` not supported by Emergent proxy** — polling endpoint gracefully reports DB state; webhook is source of truth for plan activation. Users completing real payment have plan activated within seconds via webhook.
- Job + email data is MOCK (10 jobs, 5 emails per user) — clearly labeled `source: "mock"`.

## Test Credentials
See `/app/memory/test_credentials.md` — Bearer `test_session_career_os` (user_testseed01).

## Deployment
Ready for native Emergent deployment. `deployment_agent` returned PASS in iteration 1.
