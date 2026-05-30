# Career-OS-v2: Production Deployment Guide

Status: POST-STAGING VALIDATION
Date: After 24-hour staging monitoring completes

## OBJECTIVE

Deploy to production after successful staging validation.

## PRE-PRODUCTION CHECKLIST

Before proceeding, verify ALL staging requirements passed:

- [ ] 24-hour monitoring completed
- [ ] Health endpoint: 200 OK (consistent)
- [ ] Response time: < 2s
- [ ] No error patterns
- [ ] Memory stable
- [ ] No exceptions in logs

## PRODUCTION DEPLOYMENT STEPS

### PHASE 1: Create Production Backend Service

1. Go to: https://dashboard.render.com
2. New+ → Web Service
3. Name: career-os-backend-prod (IMPORTANT: -prod, not -staging)
4. Repo: hatemamr443-byte/Career-OS-v-2 (main branch)
5. Build: pip install --upgrade pip && pip install -r backend/requirements.txt
6. Start: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
7. Environment Variables: (SAME as staging)
   - MONGO_URL
   - DB_NAME=career_os
   - STRIPE_SECRET_KEY
   - All LLM/AI keys
   - ADMIN_TOKEN
   - CRON_TOKEN
   - ENVIRONMENT=production (CHANGE FROM STAGING!)
8. Deploy → Wait 5-10 min

### PHASE 2: Create Production Frontend Service

1. New+ → Static Site
2. Name: career-os-frontend-prod (IMPORTANT: -prod, not -staging)
3. Repo: hatemamr443-byte/Career-OS-v-2 (main branch)
4. Build: cd frontend && npm ci && npm run build
5. Publish: frontend/build
6. Environment Variables:
   - REACT_APP_BACKEND_URL=https://career-os-backend-prod.onrender.com
   - REACT_APP_STRIPE_PUBLISHABLE_KEY=<key>
7. Deploy → Wait 3-5 min

## POST-PRODUCTION VALIDATION

```bash
./POST_DEPLOYMENT_VALIDATION.sh \
  https://career-os-backend-prod.onrender.com \
  https://career-os-frontend-prod.onrender.com
```

Expected: All tests PASS

## PRODUCTION MONITORING

Run for 24 hours:

```bash
./DEPLOYMENT_MONITORING.sh \
  https://career-os-backend-prod.onrender.com \
  24
```

Check logs every 6 hours:
- [ ] Health: 200 OK
- [ ] Response time: < 2s
- [ ] No errors
- [ ] Memory stable

## CRITICAL DIFFERENCES

Verify in production environment:
1. ENVIRONMENT=production (NOT staging!)
2. REACT_APP_BACKEND_URL → production URL
3. All credentials correct

## ROLLBACK PROCEDURE

If critical issues:
1. Render Dashboard → Services
2. Backend → Settings → Disable Auto-Deploy
3. Click "Revert"
4. Fix in code
5. Re-deploy

## SUCCESS CRITERIA

All of these must be true:
- Health endpoint: 200 OK
- Response time: < 2s
- Error rate: < 0.1%
- Memory: Stable
- No exceptions
- Frontend: Working

After 24 hours of success:
- Create git tag: git tag -a v1.0.0-production
- Monitor continuously
- Update runbooks if needed

---

Status: READY FOR PRODUCTION DEPLOYMENT

Follow after staging validation completes.
