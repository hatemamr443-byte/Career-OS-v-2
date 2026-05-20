# Career OS — PRD (Living Document)

## Original problem statement (verbatim)
> Complete senior-level audit, refinement, orchestration redesign, UX unification,
> AI systems optimization, and production-readiness upgrade for the entire Career
> OS project — **as an evolutionary upgrade on top of the uploaded codebase**, not
> a rebuild. Preserve all features. Goal: one intelligent operating system for
> career growth.

## Architecture done (this iteration — P0 + P1)

### P0 — Foundation Cohesion ✅
- Synced uploaded Career OS codebase into `/app` (env preserved).
- Fixed 5 blocking import / syntax / scope bugs (`routes_cv`, `routes_interview`,
  `server.py`, `db.py`, `llm_service.py`).
- Added orchestration core (event_bus, memory_service, orchestrator,
  routes_orchestrator).
- GDPR/legal surfaces: CookieConsent banner (WCAG AAA 17.93:1 contrast) +
  `/terms` page.
- New Mongo indexes for `career_events`, `ai_telemetry`, `events_outbox`.

### P1 — Brain Activation ✅
- **Migrated** `routes_decision` (match, career-roi, strategic-plan, skill-gaps)
  to `orchestrator.run()` — every Decision Engine call now inherits unified
  persona + scored memory + career context + telemetry + event publish.
- **Enriched** match analysis with 4 new strategic fields:
  `trajectory_impact`, `compensation_growth_outlook`, `skill_compounding`,
  `risk_flags`.
- **Wired 6 cross-feature subscribers** in `orchestrator.wire_subscribers()`:
  - `job_rejected` → graph + `workflow_hints` for skill-gap review prompt
  - `interview_completed` → graph
  - `offer_received` → graph + `salary_comparison` seed
  - `job_applied` → memory hydration
  - `recruiter_reachout` → `interview_prep_context` pre-fill
  - `bookmark_added` → `cv_tailor_hints` for next CV session
- **Event-producing routes** wired in `routes_jobs` (apply / status /
  bookmark) and `routes_emails` (classify by class).
- **Telemetry endpoint** `/api/orchestrator/telemetry?days=N` returning
  p50/p95 latency, success rate, by-feature/by-task breakdown, event
  throughput, bus stats.
- 4 new Mongo indexes: `workflow_hints`, `interview_prep_context`,
  `cv_tailor_hints`, `salary_comparison` (all `user_id`-unique).

## User personas (preserved from existing product)
- Ambitious professionals job-searching strategically (primary).
- Career switchers needing guidance + matching.
- Remote / international workers (visa & relocation context).
- Arab professionals targeting EU markets (i18n already present).

## Core requirements (static)
- Persistent AI memory across all features.
- Unified intelligence layer; cross-feature handoffs.
- Provider-resilient (Emergent + direct fallback Anthropic/OpenAI/Gemini).
- GDPR-compliant (export, delete, consent, cookie banner, ToS, Privacy).
- All existing features preserved (CV tailor, ATS, interview prep, salary,
  decision engine, gamification, referrals, billing, daily digest, chrome
  extension, multi-source job aggregation).

## Prioritized backlog
### P1 — Brain Activation (next iteration)
- Migrate `routes_decision`, `routes_cv`, `routes_interview` to call
  `orchestrator.run()` (replaces direct `llm_call`).
- Circuit breaker per provider in `llm_service.py`.
- AI telemetry dashboard (admin).
- **Command Center Dashboard** redesign (single hero + 3 signal tiles).
- Workflow handoffs (Job → CV Tailor prefetch match context).
- Align direct fallback model versions with Emergent routing.

### P2 — Strategic Differentiation
- Skill growth forecasting · salary trajectory forecasting.
- Relocation / visa analyzer.
- Onboarding redesign (4-step ritual to aha).
- Habit loops + re-engagement emails.
- Stripe paywall timing experiments.

### P3 — Defensibility & Scale
- Vector memory (Mongo Atlas vector / Pinecone).
- AI golden-set regression suite.
- Playwright E2E + GitHub Actions CI.
- Per-IP rate limiting (slowapi).
- Backup runbook.

## Validation / smoke tests done
- `GET /health` → 200, db connected.
- `GET /api/` → 200.
- `GET /api/orchestrator/health` → 200, 3 subscribers wired, Emergent provider OK.
- Frontend builds, Landing renders.
- `/terms` page renders with `data-testid="terms-page-title"`.
- Cookie banner mounts globally (`data-testid="cookie-consent-banner"`).
- Backend lint: clean for new modules (`event_bus`, `orchestrator`,
  `memory_service`).
- Frontend lint: clean for new components.

## Next tasks (immediate)
1. Run testing agent to validate orchestrator endpoints + cookie consent +
   terms page + GDPR endpoints end-to-end.
2. Begin P1 migration of `routes_decision` to call `orchestrator.run()`.
