# Career OS — Codebase Reference Map

> **Load this file before any review task.** Contains the full architecture,
> file index, route map, event map, and dependency graph for all 42 backend
> files + 22 frontend pages. Updated to reflect actual code state.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAREER OS SYSTEM                          │
├──────────────────┬──────────────────────────────────────────────┤
│  FRONTEND        │  BACKEND (FastAPI)                           │
│  React/CRA       │                                              │
│  22 pages        │  server.py ─── config.py ─── logging_config │
│  src/pages/      │      │                                        │
│  src/components/ │  ┌───┴──────────────────────────────────┐    │
│                  │  │         ORCHESTRATOR (Central AI Hub) │    │
│  Layout.jsx      │  │  run() → llm_service → Emergent/APIs  │    │
│  Dashboard.jsx   │  │  build_system_prompt()                │    │
│  Jobs.jsx        │  │  wire_subscribers() → EventBus        │    │
│  CVTailor.jsx    │  └──┬──────────┬──────────┬─────────────┘    │
│  Interview.jsx   │     │          │          │                   │
│  Salary.jsx      │  Memory    Career      Insights               │
│  Coach.jsx       │  Service   Intel       Service                │
│  DecisionEngine  │  (recall)  (context)   (synthesis)           │
│  CareerMap.jsx   │     │          │          │                   │
│                  │  ──────── EventBus ────────                   │
│                  │  career_events  │  events_outbox              │
│                  │  activity_logs  │  ai_telemetry               │
└──────────────────┴─────────────────────────────────────────────-┘
```

---

## Backend Files — Full Index

### Infrastructure Layer

| File | L | Purpose | Key exports |
|------|---|---------|-------------|
| `server.py` | ~240 | App entry. Registers 21 routers, CORS, RequestID middleware, startup, cron endpoints | `app` |
| `config.py` | 149 | Typed settings from env vars. Feature flags: `has_sentry`, `has_stripe`, `has_any_llm` | `settings` |
| `logging_config.py` | ~90 | JSON logs (prod) + coloured dev. Called first after dotenv load | `configure_logging()` |
| `db.py` | ~40 | Motor async collections. All exported as globals | `db, users, profiles, jobs, applications, career_events, activity_logs, cv_versions, interview_sessions, missions, …` |
| `models.py` | ~60 | Pydantic models + prefixed ULID generator | `new_id(prefix)` |
| `auth.py` | 137 | Emergent Google OAuth. Session validation. FastAPI dep | `get_current_user` |

### AI Intelligence Layer

| File | L | Purpose | Key exports |
|------|---|---------|-------------|
| `orchestrator.py` | ~180 | **Central AI hub.** Every AI call flows here. Injects persona+memory+context+telemetry+events | `orchestrator.run()`, `build_system_prompt()`, `wire_subscribers()` |
| `llm_service.py` | ~200 | Provider chain: Emergent → Anthropic → OpenAI → Gemini. Circuit breaker + timeout (45s) + retry (×2) | `llm_call()`, `parse_json_loose()`, `llm_health_check()`, `_cb` |
| `career_intelligence.py` | 325 | **Unified Brain.** Context at 3 depths (minimal/standard/full). Career graph. Cross-feature signals | `CareerIntelligence.get_context()`, `.cross_feature_signals()`, `.update_ai_notes()` |
| `memory_service.py` | ~220 | Decay-scored recall. Merges `career_events`+`activity_logs`. Weighted by event type+age | `MemoryService.recall()`, `.recall_v2()`, `.recall_prompt_block()`, `MEMORY_WEIGHTS` |
| `insights_service.py` | ~180 | Pure-aggregation insight synthesis (no AI). Patterns from cross-feature data | `generate_insights()` |
| `memory_consolidation.py` | ~110 | Background cron: events → AI notes → career_graph. Runs daily, skips users updated < 7 days | `consolidate_user_memory()`, `run_consolidation_batch()` |

### Event / Activity Layer

| File | L | Purpose |
|------|---|---------|
| `event_bus.py` | ~130 | In-process pub/sub + durable outbox. Subscriber isolation | `publish()`, `subscribe()`, `stats()`, `recent()` |
| `activity.py` | 29 | Single `log_activity()` used by all routes | `log_activity()` |
| `xp.py` | ~80 | XP engine, streak, level-up notifications | `award_xp()` |
| `notifications.py` | ~90 | In-app notification writer | `create_notification()` |

### Route Modules

| File | Prefix | Endpoints | AI? |
|------|--------|-----------|-----|
| `auth.py` | `/api/auth` | POST /session, GET /me, POST /logout | ❌ |
| `routes_profile.py` | `/api/profile` | GET /, PUT /, POST /parse-cv, POST /upload-cv | ✅ cv_parse |
| `routes_jobs.py` | `/api/jobs` | GET /feed, POST /, PUT /{id}, POST /ingest, POST /{id}/compute-match | ✅ job_match |
| `routes_cv.py` | `/api/cv` | POST /ats-score, POST /tailor, POST /cover-letter, GET /versions | ✅ cv_ats/tailor/cover_letter |
| `routes_cv_intel.py` | `/api/cv-intel` | POST /tailor/{jid}, /cover-letter/{jid}, /ats/{jid} | ✅ cv_intel |
| `routes_interview.py` | `/api/interview` | POST /questions, POST /evaluate, GET /company-research, GET/POST /sessions | ✅ interview_* |
| `routes_salary.py` | `/api/salary` | POST /range, /evaluate-offer, /negotiate, GET /cost-of-living | ✅ salary_* |
| `routes_decision.py` | `/api/decision` | POST /analyze, GET /risk-score, POST /career-roi | ✅ decision_* |
| `routes_gamification.py` | `/api/gamification` | GET /state, GET /missions, POST /coach-chat, GET /xp/history | ✅ coach_chat/missions |
| `routes_insights.py` | `/api/insights` | GET / | ❌ aggregation |
| `routes_onboarding.py` | `/api/onboarding` | GET /progress | ❌ |
| `routes_activity.py` | `/api/activity` | GET /feed, GET /stats | ❌ |
| `routes_billing.py` | `/api/billing` | POST /subscribe, /cancel, GET /status, POST /webhook | ❌ |
| `routes_gmail.py` | `/api/gmail` | GET /auth, /callback, GET /emails, POST /process | ❌ |
| `routes_gdpr.py` | `/api/gdpr` | GET /export, DELETE /delete-account | ❌ |
| `routes_emails.py` | `/api/emails` | POST /classify | ✅ email_classify |
| `routes_notifications.py` | `/api/notifications` | GET /, POST /{id}/read | ❌ |
| `routes_orchestrator.py` | `/api/orchestrator` | GET /health, GET /context, POST /run | ✅ |
| `routes_admin.py` | `/admin` | GET /telemetry, /event-bus, /circuit-breakers, POST /outbox/replay, GET /memory/{uid}, GET /system | ❌ |

### Support Modules

| File | L | Purpose |
|------|---|---------|
| `ai_limits.py` | 156 | Per-feature daily quota. Returns 429 when exceeded |
| `quota.py` | 79 | Plan match quota (free=5/mo, pro=∞) |
| `daily_digest.py` | 129 | Email digest via cron. Top 3 job matches per user |
| `emailer.py` | ~80 | Resend sender + `render_daily_digest()` |
| `welcome_emails.py` | ~120 | Day 0/1/3/7 drip sequences |
| `job_sources.py` | 376 | Connectors: Adzuna, Jooble, Remotive, WeWorkRemotely, RemoteOK, Net-empregos. Unified 15s timeout |
| `seed.py` | ~60 | Dev seed data |

---

## Feature → Orchestrator Map

| feature | task | route file | session prefix |
|---------|------|-----------|----------------|
| `cv_parse` | reasoning | routes_profile | `cv_parse_` |
| `cv_ats` | structured | routes_cv | `ats_` |
| `cv_tailor` | reasoning | routes_cv | `tailor_` |
| `cv_cover_letter` | reasoning | routes_cv | `covltr_` |
| `cv_intel` | reasoning | routes_cv_intel | — |
| `interview_questions` | reasoning | routes_interview | `iq_` |
| `interview_evaluate` | fast | routes_interview | `eval_` |
| `interview_research` | fast | routes_interview | `cmp_` |
| `salary_range` | fast | routes_salary | `sal_` |
| `salary_evaluate_offer` | fast | routes_salary | `ofr_` |
| `salary_negotiate` | reasoning | routes_salary | `neg_` |
| `salary_col` | fast | routes_salary | `col_` |
| `coach_chat` | reasoning | routes_gamification | `coach_` |
| `daily_missions` | reasoning | routes_gamification | `missions_` |
| `job_match` | reasoning | routes_jobs | `match_` |
| `email_classify` | fast | routes_emails | `email_` |
| `memory_consolidation` | fast | memory_consolidation | `memconsolidate_` |

---

## Event Map

```
event_type              publisher                    subscribers (wire_subscribers)
──────────────────      ─────────────────────        ─────────────────────────────
job_applied             routes_jobs                  memory_service.record + career_intelligence.update_graph
job_rejected            routes_jobs                  memory_service.record + rejection_streak detection
offer_received          routes_jobs                  memory_service.record (weight=25)
interview_completed     routes_interview             memory_service.record + graph update
cv_tailored             routes_cv                    memory_service.record + activity_log
salary_research         routes_salary                memory_service.record
match_analyzed          routes_jobs                  telemetry only
memory_consolidation    memory_consolidation.py      career_graph.ai_notes update
```

---

## MongoDB Collections

| Collection | Key fields | Writer | Reader |
|-----------|-----------|--------|--------|
| `users` | user_id, plan, xp, level, streak | auth | all |
| `profiles` | user_id, cv_text, skills, target_roles | routes_profile | orchestrator, cv, jobs |
| `jobs` | job_id, title, company, seniority, source | routes_jobs, job_sources | jobs, digest |
| `applications` | user_id, job_id, status | routes_jobs | insights, career_intelligence |
| `career_events` | user_id, event_type, data | wire_subscribers | memory_service |
| `activity_logs` | user_id, event_type, title, metadata | activity.py | memory_service.recall_v2 |
| `ai_telemetry` | user_id, feature, latency_ms, success | orchestrator.run | routes_admin, billing |
| `events_outbox` | event_type, user_id, data, delivered | event_bus | routes_admin /outbox/replay |
| `career_graph` | user_id, skill_graph, ai_notes, notes_updated_at | career_intelligence | orchestrator context |
| `cv_versions` | user_id, job_id, tailored_cv, keywords_added | routes_cv | routes_cv |
| `interview_sessions` | user_id, job_id, questions, evaluations | routes_interview | routes_interview |

---

## Dependency Graph

```
server.py
  ├── config.py
  ├── logging_config.py
  ├── auth.py              → models, db, welcome_emails
  ├── orchestrator.py      → llm_service, memory_service, career_intelligence, event_bus, db
  ├── memory_service.py    → db
  ├── career_intelligence.py → db
  ├── event_bus.py         → db
  ├── activity.py          → db, models
  ├── xp.py                → db, notifications, activity
  ├── ai_limits.py         → db, quota
  ├── routes_*.py          → auth, db, orchestrator, llm_service, activity, xp, ai_limits
  ├── routes_admin.py      → db, event_bus, llm_service, memory_service, career_intelligence
  ├── daily_digest.py      → db, job_sources, emailer
  └── memory_consolidation.py → db, orchestrator, career_intelligence
```

---

## Quick Change Guide

| Task | File | What to touch |
|------|------|--------------|
| Add AI feature | any routes_*.py | `orchestrator.run(feature="name", ...)` + add to `ai_limits.py` |
| Add event | any routes_*.py | `publish_event=` param + handler in `wire_subscribers()` + weight in `MEMORY_WEIGHTS` |
| Change LLM routing | llm_service.py | `ROUTING` dict |
| Change memory scoring | memory_service.py | `MEMORY_WEIGHTS` dict |
| Change context depth | career_intelligence.py | `get_context(depth=...)` |
| Add admin endpoint | routes_admin.py | Requires `ADMIN_TOKEN` header |
| Change env defaults | config.py | `Settings` class |
