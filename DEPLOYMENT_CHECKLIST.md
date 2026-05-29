# DEPLOYMENT READINESS CHECKLIST

**Status:** Ready for staging deployment  
**Last Updated:** May 28, 2026

---

## PRE-DEPLOYMENT (DO BEFORE RENDER)

### Security & Credentials
- [ ] GitHub token rotated/revoked
  - Used token: `<ROTATE_THIS_TOKEN>`
  - Go to: https://github.com/settings/tokens
  - Create new token for production

- [ ] MongoDB Atlas verified
  - [ ] Connection string correct in env.secrets
  - [ ] Test from local machine: `mongosh "<MONGO_URL>"`
  - [ ] IP whitelist includes Render IPs (0.0.0.0/0 for staging is OK)
  - [ ] Database `career_os` exists or will be created

- [ ] Stripe keys verified
  - [ ] STRIPE_SECRET_KEY is test key (sk_test_)
  - [ ] STRIPE_WEBHOOK_SECRET is ready (optional for staging)
  - [ ] Webhook not configured yet (do after deployment)

- [ ] Other credentials checked
  - [ ] LLM keys valid (EMERGENT, ANTHROPIC, OPENAI, GEMINI)
  - [ ] Email API key valid (RESEND)
  - [ ] Job API keys valid (ADZUNA, JOOBLE)
  - [ ] Admin token rotated (old: A7OEZf6H3AupSKSaLe5lR1Z2W8bF0cVyxN)
  - [ ] Cron token rotated (old: -CyZnUeu4BtimGNkrUYWEBZJm9W6seFNSLFLHLR1iqTM)

### Code Review
- [ ] All fixes verified in GitHub
  - [ ] MongoDB failfast: backend/db.py
  - [ ] Stripe webhook security: backend/routes_billing.py
  - [ ] Trial race condition: backend/routes_billing.py
  - [ ] Config integration: backend/config.py, server.py, routes_admin.py
  - [ ] Input validation: backend/models.py
  - [ ] Node version: .github/workflows/ci.yml

- [ ] No secrets in git
  - [ ] Run: `git log -p --all -S "sk_test_" | head -20`
  - [ ] Should return empty
  - [ ] Run: `git log -p --all -S "mongodb+srv" | head -20`
  - [ ] Should return empty

- [ ] All tests pass locally
  - [ ] Unit tests: `cd backend && python -m pytest tests/`
  - [ ] Syntax check: `python -m py_compile backend/*.py`
  - [ ] Import check: `python -c "from backend import db; from backend import config"`

---

## RENDER DEPLOYMENT STEPS

### Step 1: Backend Service
- [ ] Go to https://dashboard.render.com
- [ ] Click "New+" → "Web Service"
- [ ] Connect GitHub:
  - [ ] Repository: `hatemamr443-byte/Career-OS-v-2`
  - [ ] Branch: `main`
  - [ ] Name: `career-os-backend-staging`
  
- [ ] Build & Start settings:
  - [ ] Build Command: `pip install --upgrade pip && pip install -r backend/requirements.txt`
  - [ ] Start Command: `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`
  
- [ ] Health Check:
  - [ ] Path: `/health`
  - [ ] Interval: 30 seconds
  - [ ] Timeout: 10 seconds
  - [ ] Retries: 5

- [ ] Environment Variables (copy from env.secrets):
  - [ ] MONGO_URL
  - [ ] DB_NAME=career_os
  - [ ] STRIPE_SECRET_KEY
  - [ ] STRIPE_WEBHOOK_SECRET (leave empty for now)
  - [ ] EMERGENT_LLM_KEY
  - [ ] ANTHROPIC_API_KEY
  - [ ] OPENAI_API_KEY
  - [ ] GEMINI_API_KEY
  - [ ] RESEND_API_KEY
  - [ ] ADZUNA_APP_ID
  - [ ] ADZUNA_API_KEY
  - [ ] JOOBLE_API_KEY
  - [ ] CRON_TOKEN
  - [ ] ADMIN_TOKEN
  - [ ] ENVIRONMENT=staging
  - [ ] CORS_ORIGINS=*

- [ ] Click "Deploy"
- [ ] ⏱️ Wait 5-10 minutes for deployment

### Step 2: Frontend Service
- [ ] Go to https://dashboard.render.com
- [ ] Click "New+" → "Static Site"
- [ ] Connect same GitHub repo
- [ ] Settings:
  - [ ] Name: `career-os-frontend-staging`
  - [ ] Build Command: `cd frontend && npm ci && npm run build`
  - [ ] Publish Directory: `frontend/build`

- [ ] Environment Variables:
  - [ ] REACT_APP_BACKEND_URL=https://career-os-backend-staging.onrender.com
  - [ ] REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_...

- [ ] Click "Deploy"
- [ ] ⏱️ Wait 3-5 minutes for deployment

---

## POST-DEPLOYMENT VERIFICATION (AFTER RENDER ✓)

### Backend Health Tests
- [ ] Health endpoint returns 200
  ```bash
  curl https://career-os-backend-staging.onrender.com/health
  # Expected: {"status": "ok", "db": "connected"}
  ```

- [ ] Readiness endpoint returns 200
  ```bash
  curl https://career-os-backend-staging.onrender.com/health/ready
  # Expected: {"ready": true, "checks": {...}}
  ```

- [ ] Admin endpoint requires token
  ```bash
  curl -H "x-admin-token: WRONG" \
    https://career-os-backend-staging.onrender.com/admin/system
  # Expected: 403 Forbidden
  ```

- [ ] Admin endpoint works with correct token
  ```bash
  curl -H "x-admin-token: <ADMIN_TOKEN>" \
    https://career-os-backend-staging.onrender.com/admin/system
  # Expected: 200 OK with system info
  ```

### Database Tests
- [ ] Database is accessible (check Render logs)
  - [ ] No "MONGO_URL not set" errors
  - [ ] No connection timeout errors
  - [ ] MongoDB ping successful

- [ ] Collections created automatically
  - [ ] users
  - [ ] career_events
  - [ ] trial_activations
  - [ ] payment_transactions

### Billing Tests
- [ ] Trial activation works (atomic operation)
  - [ ] Create test user account
  - [ ] Call /api/billing/start-trial
  - [ ] ✅ First call succeeds
  - [ ] Call again immediately
  - [ ] ❌ Second call fails with "already used"

- [ ] Checkout creates session
  - [ ] Call /api/billing/checkout with valid plan_id
  - [ ] ✅ Returns Stripe session URL
  - [ ] Check Render logs: no errors

### Admin Tests
- [ ] CRON_TOKEN protection works
  ```bash
  curl -X POST -H "x-cron-token: WRONG" \
    https://career-os-backend-staging.onrender.com/api/internal/run-daily-digest
  # Expected: 401 Unauthorized
  ```

### CORS Tests
- [ ] Frontend can call backend
  - [ ] Visit https://career-os-frontend-staging.onrender.com
  - [ ] Check browser console: no CORS errors
  - [ ] API calls work (login, profile, etc.)

### Security Tests
- [ ] Secrets not exposed in logs
  - [ ] Check Render backend logs
  - [ ] No "STRIPE_SECRET_KEY=" visible
  - [ ] No "MONGO_URL=" visible
  - [ ] No token values visible

- [ ] Error messages don't leak info
  - [ ] Call endpoints with wrong params
  - [ ] Check error responses
  - [ ] No stack traces with file paths
  - [ ] Generic error messages only

---

## MONITORING (24 HOURS)

### Log Monitoring
- [ ] Render dashboard → Backend Service → Logs
- [ ] Watch for:
  - [ ] Startup errors (none expected)
  - [ ] Database connection errors (none expected)
  - [ ] Unhandled exceptions (none expected)
  - [ ] Performance issues (slow responses)

### Metrics
- [ ] CPU usage normal (<50%)
- [ ] Memory usage normal (<256MB)
- [ ] Response times < 2 seconds
- [ ] Error rate = 0%

### Manual Tests (Run periodically)
- [ ] `/health` still returns 200
- [ ] Admin endpoint still protected
- [ ] Trial activation still atomic
- [ ] No new error patterns in logs

---

## ROLLBACK PLAN (IF DEPLOYMENT FAILS)

### If Backend Won't Start
1. Go to Render dashboard → Backend Service
2. Click "Deployments" tab
3. Select previous working deployment
4. Click "Redeploy"
5. Wait 5 minutes and test

### If Database Connection Fails
1. Check Render backend logs for connection string
2. Verify MONGO_URL in environment variables
3. Test connection from local machine
4. Update environment variable if needed
5. Trigger manual redeploy

### If Frontend Shows Errors
1. Check browser console for CORS errors
2. Verify REACT_APP_BACKEND_URL matches backend URL
3. Check frontend build logs in Render
4. Trigger frontend redeploy

### If Stripe Webhooks Fail
1. Verify STRIPE_WEBHOOK_SECRET is set (if configured)
2. Check Stripe dashboard for webhook attempts
3. Confirm endpoint URL is correct
4. Review webhook logs in Stripe dashboard

---

## WHEN TO PROMOTE TO PRODUCTION

✅ All checks in this list: PASSED  
✅ No errors in logs (24 hours): CONFIRMED  
✅ Trial activation tested: ATOMIC (no race conditions)  
✅ Admin endpoints protected: YES  
✅ Secrets not exposed: VERIFIED  
✅ Database working: YES  
✅ Frontend/backend communicating: YES  

**Decision:** Ready to promote to production

---

## PRODUCTION DEPLOYMENT

- [ ] New GitHub token created (old one revoked)
- [ ] Backend service created with production name
- [ ] Frontend service created with production name
- [ ] Environment variables use production values
- [ ] Health checks verified
- [ ] Logs monitored continuously
- [ ] On-call rotation established
- [ ] Runbooks created (troubleshooting guides)

---

**Deployment by:** _________________  
**Date:** ___________  
**Status:** ☐ Staging ☐ Production  

