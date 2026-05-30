# Career-OS-v2: Render Deployment Action Plan

Status: READY FOR EXECUTION
Date: May 30, 2026
Backend State: OPERATIONAL (2 bugs fixed, all tests passing)

## PHASE 1: BACKEND SERVICE (10 min)

1. Go to: https://dashboard.render.com
2. New+ → Web Service
3. Connect: hatemamr443-byte/Career-OS-v-2 (main branch)
4. Name: career-os-backend-staging
5. Build: pip install --upgrade pip && pip install -r backend/requirements.txt
6. Start: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
7. Health Path: /health (30s interval)
8. Environment Variables (copy from .env):
   - MONGO_URL
   - DB_NAME=career_os
   - STRIPE_SECRET_KEY
   - EMERGENT_LLM_KEY
   - ANTHROPIC_API_KEY
   - OPENAI_API_KEY
   - GEMINI_API_KEY
   - RESEND_API_KEY
   - ADZUNA_APP_ID
   - ADZUNA_API_KEY
   - JOOBLE_API_KEY
   - CRON_TOKEN
   - ADMIN_TOKEN
   - ENVIRONMENT=staging
   - CORS_ORIGINS=*
9. Deploy → Wait 5-10 min → Get backend URL

## PHASE 2: FRONTEND SERVICE (10 min)

1. New+ → Static Site
2. Connect: hatemamr443-byte/Career-OS-v-2 (main branch)
3. Name: career-os-frontend-staging
4. Build: cd frontend && npm ci && npm run build
5. Publish Dir: frontend/build
6. Environment Variables:
   - REACT_APP_BACKEND_URL=<backend-staging-url>
   - REACT_APP_STRIPE_PUBLISHABLE_KEY
7. Deploy → Wait 3-5 min → Get frontend URL

## VALIDATION TESTS

Run after deploy:

./POST_DEPLOYMENT_VALIDATION.sh <backend-url> <frontend-url>

Should PASS all tests:
- Health endpoint responds
- Readiness doesn't hang
- Admin endpoints protected
- Response time acceptable
- Frontend loads

## 24-HOUR MONITORING

Check every 6 hours:
1. Render logs (no errors)
2. Health endpoint (200 OK)
3. Response time (< 2s)
4. Memory usage (stable)
5. Error rate (0%)

## SUCCESS CRITERIA

After 24 hours, if all pass:
- Deploy to production
- Use same services names but "-prod"
- Monitor continuously

Status: READY FOR EXECUTION
