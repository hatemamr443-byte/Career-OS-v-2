# Career-OS-v2: Production Deployment & SaaS Integration Spec

## 🎯 Mission

Transform **Career-OS-v2** from "almost production-ready" → "fully deployed SaaS backend with Stripe payments on Render"

**Success Criteria:**
- ✅ Zero runtime crashes (100% import safety)
- ✅ Deployable on Render (uvicorn entrypoint)
- ✅ Fully SaaS-ready (Stripe integration complete)
- ✅ 100% test suite passing

---

## 📋 Current State Assessment

### ✅ What's Already Done
- **52 commits** — 6-9 iterations completed
- **Stripe webhook skeleton** — basic setup in routes_billing.py
- **Trial system** — 7-day free trial (start-trial endpoint)
- **Architecture docs** — memory/, routes documented
- **Render.yaml** — deployment config ready

### ⚠️ What Needs Hardening
1. **Event Bus** — outbox reliability, retry logic, dedup
2. **Memory System** — repo-only access enforcement
3. **Orchestrator** — full telemetry, no silent failures
4. **Observability** — trace propagation (trace_id, event_id)
5. **Admin Panel** — ensure all /admin/* routes work
6. **Config System** — strict fail-fast on missing env vars
7. **Stripe Payment Flow** — complete subscription lifecycle
8. **Production Stability** — async bugs, import order, startup validation

---

## 🛠️ Production Hardening Checklist

### Phase 1: Core Stability
- [ ] Audit all imports (no circular deps)
- [ ] Fix async/await mismatches
- [ ] Validate startup sequence (dotenv → config → routes)
- [ ] Ensure health check works (DB ping)
- [ ] Test local uvicorn startup

### Phase 2: Event System
- [ ] Outbox table reliability (no orphaned events)
- [ ] Retry mechanism (exponential backoff)
- [ ] Deduplication (idempotency keys)
- [ ] Subscriber isolation (no cascade failures)

### Phase 3: Memory System
- [ ] Enforce repository-only access
- [ ] Memory consolidation pipeline
- [ ] No direct MongoDB access outside repos

### Phase 4: Orchestrator
- [ ] Full telemetry logging
- [ ] Never silently fail
- [ ] Trace propagation (orchestrator_run_id)
- [ ] Error handling (circuit breaker)

### Phase 5: Stripe SaaS
- [ ] Subscription creation endpoint
- [ ] Webhook handler (checkout.session.completed)
- [ ] Payment verification (/verify-subscription)
- [ ] Plan management (Pro, Team, Enterprise)
- [ ] Billing history endpoint

### Phase 6: Config & Env
- [ ] Use settings object everywhere
- [ ] Fail-fast on missing keys
- [ ] Clear error messages
- [ ] Render env setup docs

### Phase 7: Testing & Deployment
- [ ] pytest -q (100% passing)
- [ ] Docker build & test
- [ ] Render blueprint validation
- [ ] Health check endpoint

---

## 🏗️ Architecture Constraints

### ❌ DO NOT
- Remove any features
- Rewrite architecture from scratch
- Break API contracts
- Replace real logic with mocks in prod
- Delete event bus / memory / orchestrator
- Assume API keys exist (ask user)

### ✅ DO
- Use `app.core.config.settings` for all config
- Ask user for missing Stripe keys
- Preserve all existing routes
- Keep memory system (don't do direct DB)
- Log all operations (no silent failures)

---

## 💳 Stripe Integration Specifics

### Required Environment Variables
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Plan Structure (Server-side)
```python
PLANS = {
    "pro":  {"name": "Pro",  "amount": 19.00, "days": 30},
    "team": {"name": "Team", "amount": 49.00, "days": 30},
}
```

### Payment Flow
1. `POST /api/billing/create-checkout` → session.id
2. Client redirects to Stripe Checkout
3. `POST /api/webhook/stripe` ← Stripe webhook
4. `GET /api/billing/verify-subscription` → subscription status

---

## 🚀 Render Deployment

### Start Command
```bash
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

### Health Check
```
GET /health
Expected: {"status": "ok", "db": "connected"}
```

### Environment Setup
1. Set MONGO_URL (MongoDB Atlas)
2. Set CORS_ORIGINS (frontend URL)
3. Set Stripe keys (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET)
4. Set CRON_TOKEN (for scheduled jobs)

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Startup time | <10s | TBD |
| Health check | 200 OK | TBD |
| Stripe webhook | 200 OK | TBD |
| Test coverage | 100% pass | TBD |
| Import errors | 0 | TBD |
| Async issues | 0 | TBD |

---

## 📝 Commits Strategy

```bash
1. chore(deploy): prepare Render production deployment configuration
2. fix(core): stabilize event bus lifecycle and retry system
3. fix(memory): enforce repository-only architecture
4. fix(config): enforce strict fail-fast configuration system
5. feat(saas): add Stripe subscription and billing support
6. fix(observability): stabilize distributed tracing system
7. fix(tests): stabilize async mocks and integration suite
8. fix(startup): ensure uvicorn entrypoint works on Render
```

---

## 🔐 Security Checklist

- [ ] No API keys in code (all from env)
- [ ] Stripe webhook validation (signature check)
- [ ] CORS properly configured
- [ ] Admin endpoints protected (ADMIN_TOKEN)
- [ ] Sensitive logs redacted
- [ ] No SQL injection (MongoDB parameterized)

