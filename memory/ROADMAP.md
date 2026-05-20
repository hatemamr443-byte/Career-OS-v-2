# Career OS — Phased Roadmap

> Principle: **evolve, don't rebuild.** Each phase ships independently and is
> safe to deploy. No feature is removed.

---

## P0 — Foundation Cohesion (THIS ITERATION) ✅

* ✅ Fix `emergent_err` scope bug in `llm_service.py`.
* ✅ Fix `routes_cv.py` undefined `job_title` / `job_company`.
* ✅ Fix `routes_interview.py` broken `try:` block (research summary).
* ✅ Fix `server.py` missing `Request` import for cron route.
* ✅ Fix `db.py` missing `referrals` + `ai_usage` exports.
* ✅ Add **EventBus** (`backend/event_bus.py`) — in-process pub/sub w/ Mongo
  durability.
* ✅ Add **MemoryService** (`backend/memory_service.py`) — scored recall.
* ✅ Add **Orchestrator** (`backend/orchestrator.py`) — unified AI entry point
  with shared persona, memory injection, and event publishing.
* ✅ Add **AI Telemetry** collection + middleware hook.
* ✅ Add `/api/orchestrator/health` + `/api/orchestrator/recent-events`.
* ✅ Add new `career_events(user_id, event_type, created_at desc)` index.
* ✅ Frontend: **CookieConsent banner** on every page until accepted.
* ✅ Frontend: **`/terms` Terms of Service page**.
* ✅ `/app/memory/AUDIT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `PRD.md`.

---

## P1 — Brain Activation (✅ THIS ITERATION)

Organized by strategic dimension as approved.

### 🧱 Architectural Debt
* ✅ Migrated `routes_decision` (match, career-roi, strategic-plan, skill-gaps)
  to call `orchestrator.run()` instead of `llm_call()` directly. Response
  shapes preserved → backward-compatible.
* ⏳ Migrate `routes_cv` + `routes_interview` to orchestrator (next iter).
* ⏳ Align direct fallback model versions in `llm_service.py` with Emergent
  routing (gpt-5.1 / gemini-3-flash) — current drift to `gpt-4o-mini` /
  `gemini-1.5-flash` is a fallover capability mismatch.

### 🎨 UX Evolution
* ✅ **Brain Reveal Layer** (thin, additive) — `/api/orchestrator/insights` +
  `BrainReveal.jsx` mounted above KPI strip on the existing Dashboard.
  Renders nothing when empty. Up to 5 typed cards with: headline, detail,
  source signals, confidence, primary action, dismiss. Unified voice ("Career
  OS noticed…"). Sources: salary_comparison, workflow_hints (skill-gap
  review), interview_prep_context (recruiter reachout pre-fill),
  cv_tailor_hints (bookmark pre-load), high-interest-companies derived signal.
* (Still deferred per guardrail — no broad Dashboard redesign yet.)
* The "one brain" feeling now visibly emerges through Brain Reveal cards
  while the rest of the UX remains unchanged.

### 🧠 Orchestration Expansion
* ✅ **6 cross-feature subscribers wired** (in `orchestrator.wire_subscribers`):
  * `job_rejected`        → records to graph + writes `workflow_hints` flag
                            so the next Dashboard load can prompt skill-gap review.
  * `interview_completed` → records to graph (strong/weak areas extraction).
  * `offer_received`      → seeds `salary_comparison` collection so Salary
                            page can show market context without fresh AI call.
  * `job_applied`         → memory hydration via durable career_events.
  * `recruiter_reachout`  → seeds `interview_prep_context` so Interview Prep
                            page pre-fills company research the moment it opens.
  * `bookmark_added`      → seeds `cv_tailor_hints` so CV Tailor can suggest
                            tailoring for the freshly saved role.
* ✅ **Event-producing routes** wired (fire-and-forget, never blocks request):
  * `routes_jobs.create_application`         → `job_applied`
  * `routes_jobs.update_application_status`  → `job_rejected` / `offer_received`
                                               / `interview_scheduled`
  * `routes_jobs.bookmark_job`               → `bookmark_added`
  * `routes_emails.classify_email`           → `recruiter_reachout` /
    `interview_invited` / `offer_email_received` / `rejection_email_received`
  * `routes_decision.*`                      → `match_analyzed` /
    `career_roi_analyzed` / `decision_strategic_plan` / `skill_gap_analyzed`
* ⏳ Outbox replay endpoint (admin) for failed handler recovery.
* ⏳ Wildcard (`*`) subscriber for analytics fan-out.

### 🧬 Intelligence / Memory Enhancements
* ✅ Decision Engine match output enriched with strategic reasoning fields:
  `trajectory_impact`, `compensation_growth_outlook`, `skill_compounding`,
  `risk_flags` — alongside existing score/confidence/decision/etc.
* ✅ Memory scoring includes weights for new event types
  (`match_analyzed`, `decision_strategic_plan`, `salary_research`).
* ✅ `/api/orchestrator/memory` returns the user's scored memory snippets
  for preview / debug.
* ⏳ Full memory replay endpoint (admin) with event-stream filtering.
* ⏳ User-tunable memory weights per-user.
* ⏳ Semantic memory (Atlas Vector) — graduation path documented.
* ⏳ AI golden-set regression suite.

### 🛡️ Resilience / Reliability Upgrades
* ✅ Per-call telemetry → `ai_telemetry` collection (feature, task, provider,
  latency_ms, success, output_chars).
* ✅ `/api/orchestrator/telemetry?days=N` rollup endpoint returning
  p50/p95 latency, success rate, by-feature & by-task breakdown,
  event throughput counts, global bus stats.
* ⏳ Circuit breaker per provider (sliding-window error rate, half-open recovery).
* ⏳ Liveness + readiness split (`/health` vs `/health/ready` w/ LLM probe).
* ⏳ Per-IP rate limiting on auth + session endpoints.

---

## P2 — Strategic Differentiation (3–4 weeks)

* **Skill Growth Forecasting** — given current applications + market data,
  predict the user's marketability curve at 6 / 12 / 24 months.
* **Salary Trajectory Forecasting** — leverages `career_graph.salary_trajectory`.
* **Relocation / Visa analyzer** — paired with `target_locations`.
* **Market Timing analysis** — when to apply vs wait, by role + region.
* **Onboarding redesign** — 4-step ritual: import CV → set targets → first
  AI match → first AI insight (aha moment in < 2 min).
* **Habit loops & retention**:
  * Daily Digest already exists — make it a *strategic briefing* (orchestrated).
  * Streaks + missions surface in dashboard hero.
  * Re-engagement emails when memory shows 7d inactivity.
* **Stripe checkout polish + paywall timing experiments**.

---

## P3 — Defensibility & Scale (6–8 weeks)

* **Vector memory** option (Mongo Atlas vector index or Pinecone) — graduate
  `MemoryService.recall` from scored retrieval to semantic retrieval.
* **AI golden-set regression suite** — frozen prompts × known outputs, run
  pre-deploy.
* **Playwright E2E** covering signup → onboarding → apply → tailor → interview
  → digest.
* **GitHub Actions CI** — lint, pytest, Playwright on PR.
* **Per-IP rate limiting** on auth + session endpoints (slowapi).
* **Backup runbook** + restore drill quarterly.
* **Self-serve admin tools** (impersonation, user inspect, queue replay).
* **Sentry alerts** on AI failure rate spike, on 5xx spike, on Mongo lag.

---

## P4 — Investor / Category Story (parallel, ongoing)

* Public **Career OS Manifesto** page (`/manifesto`) — the one-brain thesis.
* **Case studies** with real (or beta) users showing trajectory change.
* **Open Career Graph schema** — publish the data model as a standard.
* **Embeddings of career outcomes** — proprietary moat over time.
* **Recruiter-side dashboard** (B2B revenue lane, optional).

---

## Definition of Done (per phase)

| Check | P0 | P1 | P2 | P3 |
|---|----|----|----|----|
| Linter clean (ruff + eslint) | ✅ | ✅ | ✅ | ✅ |
| Backend `/health` 200 | ✅ | ✅ | ✅ | ✅ |
| Frontend builds | ✅ | ✅ | ✅ | ✅ |
| Testing agent green | ✅ | ✅ | ✅ | ✅ |
| No removed features | ✅ | ✅ | ✅ | ✅ |
| Docs updated (`memory/*.md`) | ✅ | ✅ | ✅ | ✅ |

---

## Non-Goals (explicitly)

* Rewriting authentication.
* Replacing MongoDB.
* Moving to a different framework.
* Reducing feature surface.
* Building a B2B side before B2C "aha" is consistent.


---

## P1.5 — Production Hardening (✅ THIS PASS)

* ✅ **Circuit breaker** per provider in `llm_service.py` — sliding window (10 calls, >50% → open 60s, half-open probe).
* ✅ **Model version alignment** — `_call_openai` upgraded `gpt-4o-mini` → `gpt-4o`; `_call_gemini` upgraded `gemini-1.5-flash` → `gemini-2.0-flash-exp`.
* ✅ **`routes_cv` migrated to `orchestrator.run()`** — ats_score, tailor, cover_letter all inherit unified persona + memory + telemetry.
* ✅ **`routes_interview` migrated to `orchestrator.run()`** — questions, evaluate, company_research all migrated. Added `/sessions/{id}/complete` endpoint that fires `interview_completed` event.
* ✅ **Health endpoint split** — `/health` (liveness, always 200) vs `/health/ready` (readiness: DB + LLM probe).
* ✅ **GitHub Actions CI** — backend pytest + ruff lint, frontend build + eslint, secrets scan — runs on every push/PR to main.
* ✅ **Render.yaml production-hardened** — security headers, health check path, env var structure.
