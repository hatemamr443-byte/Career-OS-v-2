# Career OS — Target Architecture (Evolutionary)

> Goal: Career OS becomes **one intelligent operating system** with persistent
> memory, an event-driven orchestrator, and unified AI reasoning — *without*
> removing existing features.

---

## 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  L4 — SURFACE                                                       │
│  Pages / Components / AICoachDock / Career Command Center          │
│  Unified AI tone, consistent micro-interactions, progressive       │
│  disclosure, contextual handoffs between tools                     │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────────┐
│  L3 — DOMAIN ROUTES                                                 │
│  routes_jobs · routes_cv · routes_interview · routes_decision …    │
│  Thin HTTP layer — delegates to orchestrator + services            │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────────┐
│  L2 — ORCHESTRATION                                                 │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ Orchestrator     │  │ EventBus         │  │ MemoryService   │   │
│  │ (workflows,      │◀▶│ (pub/sub,        │◀▶│ (scored         │   │
│  │  AI tone,        │  │  outbox-backed)  │  │  retrieval,     │   │
│  │  context build)  │  │                  │  │  decay, recency)│   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬────────┘   │
│           │                     │                     │             │
└───────────┼─────────────────────┼─────────────────────┼─────────────┘
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  L1 — INTELLIGENCE PRIMITIVES                                       │
│  CareerIntelligence (context)  ·  LLM Service (provider failover)  │
│  AI Limits / Quotas  ·  AI Telemetry  ·  Decision Engine kernel    │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────────┐
│  L0 — DATA                                                          │
│  MongoDB (collections)  +  career_graph  +  career_events (memory) │
│  ai_telemetry  +  events_outbox  +  Mongo TTL / indexes            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. New Core Modules (introduced this iteration)

### `backend/event_bus.py`
* In-process async pub/sub. Subscribers register `(event_type, async_handler)`.
* Every published event ALSO writes to `career_events` (durability + replay).
* Failure in a subscriber is isolated (logged, not raised).
* **API**:
  ```python
  await event_bus.publish("job_rejected", user_id, {"job_id": ...})
  event_bus.subscribe("job_rejected", review_skill_gaps)
  ```

### `backend/memory_service.py`
* Reads `career_events` and `career_graph`, scores them by **recency × event-weight**.
* Returns top-K events as compact memory snippets for LLM injection.
* Decay function: `score = weight * exp(-age_days / half_life)`.
* Event weights table is small and human-tunable (`MEMORY_WEIGHTS`).

### `backend/orchestrator.py`
* The "brain". Every AI feature calls `orchestrator.run(...)` rather than
  `llm_call(...)` directly.
* Responsibilities:
  1. Build the **unified system prompt** (persona + tone + safety + memory).
  2. Call `MemoryService.recall()` and inject relevant memories.
  3. Call `CareerIntelligence.get_context_prompt()`.
  4. Invoke `llm_call()` with the right task tier.
  5. Publish completion events to the bus.
* This is where the *one-brain* feel is built.

### `backend/routes_orchestrator.py`
* `/api/orchestrator/health` — live status of provider chain + memory + bus.
* `/api/orchestrator/recent-events` — debug feed of bus activity (admin only).

---

## 3. Subscribers & Workflows (cohesion examples)

| Event published by | Triggers (subscriber) | Effect |
|---|---|---|
| `routes_jobs.apply` → `job_applied` | `MemoryService` records | Future match calls know this user applied here |
| `routes_decision.match` → `job_rejected` | `analyze_skill_gaps` (deferred) | Skill-gap insight surfaces on Dashboard |
| `routes_cv.tailor` → `cv_tailored` | `XP grant` + `streak tick` | Already exists; now via bus |
| `routes_interview.complete` → `interview_completed` | `CareerIntelligence.record_event` | Strong / weak areas update graph |
| `routes_emails.classify` → `recruiter_reachout` | `notifications.push` + `interview_prep_seed` | Inbox AI feeds Prep |

---

## 4. Unified AI Voice

Defined once in `orchestrator.SYSTEM_PERSONA`:

> *You are Career OS, a senior career strategist embedded in the user's life.
> You speak calmly, specifically, and strategically. You never give generic
> advice. You always reference what you know about this user. You optimize for
> their long-term career capital, not short-term wins. When uncertain, you
> say so.*

Every route that calls AI inherits this preamble through the orchestrator.

---

## 5. Memory Scoring Formula

```
def score(event):
    age = now - event.created_at
    half_life = HALF_LIFE[event.type]  # days
    return WEIGHT[event.type] * exp(-age.days / half_life)
```

| Event type            | Weight | Half-life (days) |
|-----------------------|--------|------------------|
| `offer_received`      | 100    | 365              |
| `interview_completed` | 60     | 90               |
| `job_rejected`        | 40     | 60               |
| `cv_tailored`         | 30     | 30               |
| `salary_research`     | 25     | 30               |
| `job_applied`         | 20     | 21               |
| `bookmark`            | 10     | 14               |
| `view`                | 3      | 3                |

`MemoryService.recall(user_id, k=8)` returns the top-K scored events
formatted as `"[2d ago] interviewed at Stripe — score 7.2"` snippets.

---

## 6. Provider Abstraction (already partially built)

```
llm_call(task)
   │
   ├── Try Emergent  (primary)
   │       └── on failure → log warning
   │
   └── Fallback chain (per task type)
           Anthropic / OpenAI / Gemini
           └── circuit-broken per provider (P1)
           └── telemetry recorded per attempt (P1)
```

Direct SDK fallback already wired. Adding direct API keys to `.env` engages
direct path automatically.

---

## 7. Data Model Evolution (non-breaking)

* `ai_telemetry` (new): `{user_id, feature, task, provider, model, latency_ms,
  prompt_tokens, completion_tokens, success, error, created_at}`
* `events_outbox` (new): mirror of pub events for at-least-once replay.
* `career_events` (existing): gains compound index
  `(user_id, event_type, created_at desc)`.
* `consent` (extends `users` doc): `{cookies, marketing, analytics,
  ai_improvement, accepted_terms_at, accepted_privacy_at}`.

---

## 8. Frontend Cohesion (this iteration adds)

* **CookieConsent.jsx** — Banner mounted in `App.js`, persists choice to
  localStorage + `/api/me/consent` when authenticated.
* **Terms.jsx** — Full Terms of Service page at `/terms`.
* (P1 next iteration) **Command Center Dashboard** — single hero "Next Move",
  three signal tiles (Pipeline / Insights / Wellbeing), bottom tool strip.
* (P1) Workflow handoffs: when navigating Job → CV Tailor, prefetch the job's
  match analysis so the tailoring system prompt already knows context.

---

## 9. Folder Convention Going Forward

```
backend/
  core/                # NEW: orchestration primitives (orchestrator, event_bus,
                       #      memory_service, ai_telemetry) — added this pass
                       #      kept flat for backwards-compat with current imports
  routes_*.py          # HTTP layer, thin
  services_*.py        # domain services (to extract from routes over time)
  llm_service.py       # provider abstraction
  career_intelligence.py # user context layer
  models.py            # Pydantic
  db.py                # Mongo accessors
```

We **do not** restructure folders in this iteration to avoid import churn —
all new modules live alongside existing ones with clear naming.
