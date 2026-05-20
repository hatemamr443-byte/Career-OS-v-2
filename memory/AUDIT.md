# Career OS — Senior-Level Architecture Audit (v2.1)

> Status: **Living document**. Last updated: 2026-02 (this iteration).
> Audience: Eng leadership, product, founding team, investors.

---

## 0. Executive Summary

Career OS today is a **feature-rich but loosely-orchestrated AI platform** with the
right ingredients for the stated vision of a *Career Intelligence Operating System*:

* A unified `CareerIntelligence` layer already exists (`career_intelligence.py`) and
  is the correct foundation — it injects user context into LLM prompts.
* The `llm_service.py` provider abstraction (Emergent primary + Anthropic / OpenAI /
  Gemini fallbacks) is mostly correct but has gaps (no circuit breaker, no per-task
  health snapshot, no latency budget, error scoping bug — *fixed in this pass*).
* The Decision Engine (`routes_decision.py`) already implements ROI analysis,
  strategic planning, burnout indicators, and skill-gap analysis.
* GDPR endpoints (export/delete/consent) exist; legal pages (Privacy/ToS) and a
  cookie consent UX are partially missing.
* The codebase is **fundamentally healthy**: clean module boundaries, async-first,
  Pydantic models, Mongo indexes created on startup, Sentry hooked.

**Gap → Vision**: features write *events* but no central **orchestrator** consumes
those events to coordinate downstream workflows. There is **no persistent
memory retrieval scoring** (career events are written but not ranked / retrieved
by relevance for AI calls). There is **no event bus** decoupling producers from
consumers. The UX presents many AI tools side-by-side; the *one-brain* feel is not
yet achieved at the surface.

This audit is the basis for the **evolutionary upgrade** delivered alongside it
(see `ARCHITECTURE.md` and `ROADMAP.md`).

---

## 1. Current System Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19 + CRA)                     │
│  Landing • Login • Pricing • Dashboard • Jobs • CVTailor             │
│  DecisionEngine • InterviewPrep • SalaryIntel • Insights • CareerMap │
│  AICoachDock • Notifications • ActivityFeed • OnboardingWidget       │
└──────────────────────────────────────────────────────────────────────┘
                              ▼ /api/*
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Motor)                         │
│                                                                       │
│   ┌─────────────┐   ┌──────────────────┐   ┌─────────────────────┐   │
│   │  Auth       │   │ Career           │   │  LLM Service        │   │
│   │  (Emergent  │   │ Intelligence     │   │  (Emergent +        │   │
│   │   OAuth)    │   │ (context +       │   │   direct fallback)  │   │
│   └──────┬──────┘   │  graph + events) │   └──────────┬──────────┘   │
│          │          └──────────────────┘              │              │
│          ▼                  ▲                         ▼              │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ routes_jobs / routes_cv / routes_interview / routes_salary /  │   │
│   │ routes_decision / routes_insights / routes_billing /          │   │
│   │ routes_emails / routes_gdpr / routes_gamification ...         │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                              ▼                                        │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ MongoDB: users • profiles • jobs • applications •            │   │
│   │ cv_versions • interview_sessions • emails • career_graph •   │   │
│   │ career_events • salary_cache • activity_logs • xp_events …   │   │
│   └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Strengths
* Clear separation of routes / domain logic / db.
* Per-collection Mongo indexes wired in `server.py:on_startup`.
* `CareerIntelligence` already passes a unified context prompt into LLM calls.
* Provider fallback chain in `llm_service.py` is *the right abstraction*.
* GDPR endpoints already shipped (export ZIP, delete, consent flags).
* Sentry integration optional via env (`SENTRY_DSN`).

### Weaknesses (the heart of this audit)
1. **No event bus.** `CareerIntelligence.record_event` writes to `career_events`
   but no consumer reacts to events. Cross-feature handoffs are implicit, not
   automated. Example: a `job_rejected` event does NOT trigger a CV skill-gap
   review, even though the data and the analyzer both exist.
2. **No memory retrieval scoring.** Memory is *stored* (career_graph,
   career_events) but never *retrieved by relevance*. Every LLM call gets the
   same generic context.
3. **No circuit breaker on LLM providers.** A consistently failing provider is
   retried on every request; latency tail is unbounded.
4. **Decision routing is task-string-based, not capability-based.** Adding a new
   model (e.g. Sora 2 video) requires editing `ROUTING` dict.
5. **No structured AI telemetry.** Tokens, latency, provider used, retries,
   cost — none tracked per call.
6. **Frontend doesn't surface the brain.** Dashboard is a tile board, not a
   *Command Center* with a single primary recommendation, a "next best action",
   and contextual signal feed.
7. **GDPR is functional but not discoverable.** No cookie consent banner, no
   ToS page (`/terms`), no in-app *Privacy Center* surface.
8. **No legal pages** beyond `Privacy.jsx`; no ToS, no DPA placeholder.
9. **No CI/CD config in repo** (only `render.yaml` for deploy).
10. **Tests are sparse** (`backend/tests/`, `frontend/plugins/health-check`),
    no Playwright E2E, no AI-output validation suite.

---

## 2. AI Architecture Audit

### Current routing (`llm_service.py`)
| Task type      | Emergent route                    | Direct fallback chain          |
|----------------|-----------------------------------|--------------------------------|
| `reasoning`    | Anthropic claude-sonnet-4-5       | Anthropic → OpenAI → Gemini    |
| `fast`         | Gemini 3 Flash preview            | Gemini → Anthropic → OpenAI    |
| `structured`   | OpenAI gpt-5.1                    | OpenAI → Anthropic → Gemini    |

### Issues
* `_call_openai` uses `gpt-4o-mini` for fallback while the Emergent path uses
  `gpt-5.1`. Capability mismatch on failover.
* `_call_gemini` uses `gemini-1.5-flash` while the Emergent path uses
  `gemini-3-flash-preview`. Same drift.
* `emergent_err` was leaking out of its `except` block scope (NameError on
  total failure). **Fixed in this pass.**
* No retry-with-backoff inside any single provider call.
* `llm_health_check` only pings Emergent; doesn't probe direct providers.

### Recommended (implemented in this iteration where marked ✅)
* ✅ Fix `emergent_err` scope bug.
* ✅ Add **Orchestrator** (`orchestrator.py`) sitting *above* `llm_service` —
  responsible for: memory injection, event publication, workflow dispatch.
* ✅ Add **EventBus** (`event_bus.py`) — async pub/sub over an in-process queue
  with optional Mongo persistence for replay.
* ✅ Add **MemoryService** (`memory_service.py`) — scored retrieval of career
  events for prompt injection.
* ⏳ (P1) Add circuit breaker per provider with sliding-window error rate.
* ⏳ (P1) Add per-call telemetry (`ai_telemetry` collection: provider, task,
  latency_ms, prompt_tokens, completion_tokens, cost_usd, success).
* ⏳ (P2) Align direct fallback model versions with Emergent routing.

---

## 3. Database Audit

### Current collections (43 confirmed via `db.py` + on_startup indexes)
`users` · `user_sessions` · `jobs` · `applications` · `emails` · `missions`
· `coach_messages` · `decisions` · `profiles` · `activity_logs`
· `notifications` · `xp_events` · `onboarding` · `bookmarks` · `cv_versions`
· `interview_sessions` · `emails_sent` · `career_graph` · `career_events`
· `salary_cache` · `referrals` · `ai_usage` · `match_usage`
· `payment_transactions`

### Issues
* `career_events` lacks a TTL / archive policy — will grow forever.
* No compound index on `career_events(user_id, event_type, created_at)`.
* `decisions` collection has no TTL — match results from a year ago still served.
* No `ai_telemetry` collection (proposed).
* No `events_outbox` for transactional event publishing (proposed).

### Recommendations
* ✅ Add index `career_events(user_id, event_type, created_at desc)` on startup
  (added in this iteration).
* ⏳ Add `decisions.updated_at` TTL of 30 days.
* ⏳ Introduce `events_outbox` if we ever move event bus out of process.

---

## 4. Frontend & UX Audit

### Current
* 19 page routes, Layout wrapper, AICoachDock floating widget, OnboardingWidget,
  ProfileCompleteness, QuotaBanner, ContextualSuggestions, NotificationsDrawer.
* TailwindCSS + Radix + shadcn/ui + framer-motion + sonner.
* I18n + Analytics + Auth contexts.

### Issues
* **Information hierarchy**: Dashboard renders many cards equally — user must
  pick what to do. No single "Today's strongest opportunity" or "Next best
  move" hero block.
* **AI tone drift**: each feature speaks slightly differently. No shared system
  prompt prefix mandating a unified Career OS voice ("strategic, calm,
  specific, never generic").
* **Workflow continuity**: clicking *Tailor CV* on a job doesn't pre-load the
  job's match analysis context. Each tool starts from zero.
* **Trust/legal**: no `/terms` route. No cookie consent banner. Privacy page
  exists but is just static text.
* **Empty states**: most pages assume data exists.

### Recommendations (P0 implemented this pass)
* ✅ Add `/terms` page (Terms of Service).
* ✅ Add **Cookie Consent banner** mounted globally (writes to
  `consent.cookies` via `/api/me/consent`).
* ⏳ (P1) Reframe Dashboard as **Career Command Center**: single primary
  recommendation card at top, with three signal tiles (Pipeline / Insights /
  Wellbeing) and a bottom strip of secondary tools.
* ⏳ (P1) Add a unified **AI tone preamble** in `orchestrator.py` so every LLM
  call inherits the same voice.

---

## 5. Production Readiness Audit

| Area | Status | Notes |
|---|---|---|
| Logging | ✅ basic | structured logging via stdlib only |
| Error monitoring | ✅ Sentry optional | needs SENTRY_DSN |
| Health endpoint | ✅ `/health` | pings Mongo |
| Liveness/readiness split | ❌ | needs `/health/ready` w/ LLM probe |
| Rate limiting | ⚠️ partial | `ai_limits.py` only on AI features |
| Abuse prevention | ❌ | no per-IP rate limit on auth/session |
| Secret management | ✅ env-based | no hardcoded secrets in this iteration |
| Backups | ⚠️ external | depends on Mongo provider |
| CI/CD | ❌ | no GH Actions / no test gates |
| Observability | ⚠️ | logs only, no metrics export |
| GDPR | ✅ functional | needs UI surface (Privacy Center) |
| Cookie consent | ❌ → ✅ this pass | banner added |
| Terms of Service | ❌ → ✅ this pass | `/terms` page added |
| Provider failover | ✅ wired | needs circuit breaker (P1) |

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Single LLM provider outage stalls all AI | Med | High | ✅ Provider fallback exists; ⏳ add circuit breaker |
| Career events table unbounded growth | High | Med | ⏳ Archive policy / TTL on low-value events |
| GDPR complaint without ToS | Med | High | ✅ ToS + cookie consent added this pass |
| AI hallucination on CV tailoring damages user trust | Med | High | ⏳ Add JSON-schema validation + golden-set regression |
| Vendor lock-in on Emergent | Low | Med | ✅ Direct SDK fallback wired |
| No CI tests → regressions ship | Med | High | ⏳ Add Playwright E2E + GH Actions |

---

## 7. What's Already Excellent (preserve, don't touch)

* `career_intelligence.py` — the conceptual core is right.
* `llm_service.py` provider abstraction shape.
* GDPR export ZIP packaging.
* Mongo index strategy on `on_startup`.
* Per-feature AI quotas (`ai_limits.py`).
* Pydantic models with `ConfigDict(extra="ignore")` for forward-compat.
* Modular `routes_*` files with clean prefix-based routing.

---

See `ARCHITECTURE.md` for the target state and `ROADMAP.md` for phasing.
