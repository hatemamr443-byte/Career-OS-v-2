# AI Career OS — PRD

## Original Problem Statement
Build a full-stack AI-powered platform that acts as a personal career assistant and decision-making system. Not a job board — a decision-driven AI system that decides, recommends, tracks, and improves the user's job search strategy. Layers: data, execution, intelligence, decision, email intelligence, lifecycle tracker, analytics, gamification (Duolingo-style), dark modern UI.

## User Choices (Feb 2026)
- **Auth**: Hybrid — Emergent Google OAuth now, JWT-ready abstraction
- **LLM**: Multi-model router — Claude Sonnet 4.5 (reasoning), Gemini 3 Flash (fast/bulk classification)
- **Jobs**: Hybrid — mock dataset + manual entry, pluggable JobSource
- **DB**: MongoDB (vector matching simulated via cosine similarity in app layer; abstracted for future Pinecone/Postgres)
- **Email**: Mock inbox with full AI pipeline (classification + intent + next steps)

## Architecture
- **Backend** (`/app/backend/`): FastAPI modular routers
  - `auth.py` — AuthService abstraction, Emergent Google OAuth
  - `routes_jobs.py` — jobs, applications, decision engine, AI match
  - `routes_emails.py` — AI-classified email threads
  - `routes_gamification.py` — daily missions (AI-generated), XP, streak, AI Coach
  - `routes_insights.py` — funnel, rates, pattern detection
  - `routes_profile.py` — CV parsing, identity graph
  - `llm_service.py` — LLM router (task → provider)
  - `seed.py` — 10 mock jobs, 5 mock emails, sample CV
- **Frontend** (`/app/frontend/src/`): React + Tailwind + shadcn + phosphor-icons
  - Dark "Swiss / Control Room" aesthetic, Cabinet Grotesk + Manrope + JetBrains Mono
  - Pages: Login, Dashboard, Jobs, JobDetail, Emails, Insights, CareerMap, Profile
  - Floating AI Coach dock (Claude-powered)

## Implemented (Apr 2026)
- ✅ Emergent Google OAuth + AuthService abstraction
- ✅ 10 seeded mock jobs with skill-based quick scoring
- ✅ AI Match Engine (Claude Sonnet 4.5) — score, decision, reasoning, strengths, gaps, expected outcome
- ✅ Decision Engine — top recommendations with ROI ranking, confidence
- ✅ Application lifecycle tracker (6 states with timeline)
- ✅ Mock recruiter inbox (5 emails) + AI classification (Gemini 3 Flash)
- ✅ Daily Missions (4 AI-generated, action_type + reasoning + xp_reward)
- ✅ Gamification: XP, level curve, streak counter, progress bar
- ✅ AI Coach floating chat (Claude with user career context)
- ✅ Insights: funnel, interview/offer/rejection rates, rejection patterns by seniority
- ✅ Career Map: kanban-style lifecycle columns
- ✅ CV editor + Claude-powered CV parsing → headline/skills/roles
- ✅ All endpoints `/api`-prefixed, MongoDB-only, _id stripped on responses

## Backlog (P0 / P1 / P2)
- P1: Real job source connectors (Indeed/LinkedIn via Playwright)
- P1: Gmail OAuth ingestion (data contracts already match Gmail schema)
- P1: Strategy Switching Engine — auto-detect low conversion + suggest pivots
- P1: Decision Replay system — record outcomes vs predictions, learn over time
- P2: Embeddings-based vector search (currently skill-overlap heuristic)
- P2: Career Map graph visualization (currently kanban; upgrade to actual graph)
- P2: Emotional/friction layer — fatigue detection, workload throttling
- P2: Anti-spam rate limits + duplicate prevention (basic dedupe via job_id+user_id unique)
- P2: GDPR data export + deletion endpoint

## Test Credentials
See `/app/memory/test_credentials.md` — Bearer `test_session_career_os` (user_testseed01).
