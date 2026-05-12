# Render Deployment Guide — AI Career OS

This project is built for **native Emergent deployment** but can be migrated to Render with the steps below.

---

## Architecture overview

| Component | Service type on Render | Build / Start | Internal port |
|---|---|---|---|
| FastAPI backend | Web Service (Python) | `pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/` / `uvicorn server:app --host 0.0.0.0 --port $PORT` | $PORT (Render assigns) |
| React frontend | Static Site | `cd frontend && yarn install && yarn build` / publish dir `frontend/build` | static |
| MongoDB | external — MongoDB Atlas | — | — |

> Note: the backend entry module is **`server`**, not `main`. The corrected start command is `uvicorn server:app --host 0.0.0.0 --port $PORT`.

---

## 1. Push the repo to GitHub

In the Emergent dashboard click **Save to GitHub** (top-right). Render deploys from GitHub.

## 2. Provision MongoDB Atlas

1. Create a free cluster at https://cloud.mongodb.com
2. Add a database user (record the password)
3. Network Access → allow `0.0.0.0/0` (Render egress IPs are dynamic)
4. Copy the connection string. Example:
   ```
   mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

## 3. Deploy the backend (Render Web Service)

1. Render dashboard → **New + → Web Service** → connect your GitHub repo
2. Settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**:
     ```
     pip install --upgrade pip && pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
     ```
     (the extra index URL is required for the `emergentintegrations` library — public CDN, no auth)
   - **Start Command**:
     ```
     uvicorn server:app --host 0.0.0.0 --port $PORT
     ```
   - **Python version**: a `runtime.txt` file ships in `/backend` pinning Python to `3.11.10`. Render's default 3.13 breaks wheels for several deps. Don't remove this file.

   ### If you see "Exited with status 1" at build time
   The CloudFront URL is fine. The culprit is almost always one of these:
   - **Bloated `requirements.txt`**: dev tools (`black`, `pytest`, `mypy`), heavy packages with native deps (`pandas`, `jq`), or unused libs (`boto3`, `cryptography`) blow up Render free tier's 512 MB build memory. The current `requirements.txt` is intentionally slim — every package is imported in the codebase. If you re-add anything, scan first.
   - **Python version**: emergentintegrations is built for 3.11. The `runtime.txt` pin handles this.
   - **Missing `--extra-index-url`** in build command — emergentintegrations is on a private CDN, not PyPI.

   The CloudFront index is at https://d33sy5i8bnduwe.cloudfront.net/simple/ — public, no token, returns 200 from any IP.
3. Environment Variables (from `backend/.env.example`):
   - `MONGO_URL` → your Atlas connection string
   - `DB_NAME` → `career_os`
   - `CORS_ORIGINS` → your future frontend URL, e.g. `https://career-os-web.onrender.com`
   - `EMERGENT_LLM_KEY` → copy from `/app/backend/.env` or your Emergent profile
   - `STRIPE_API_KEY` → keep `sk_test_emergent` for sandbox, or paste your own `sk_live_...`
   - `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` → register at https://developer.adzuna.com (free, 1000 calls/mo)
   - `ADZUNA_COUNTRIES` → comma-separated, default `es,gb`. **Portugal not supported by Adzuna** — use `es` for Iberian market.
   - `JOOBLE_API_KEY` → register at https://jooble.org/api/about
   - `JOOBLE_LOCATION` → default `Lisbon`
   - `RESEND_API_KEY` → register at https://resend.com (free 100/day)
   - `SENDER_EMAIL` → default `onboarding@resend.dev`. Use your verified domain in production.
   - `CRON_TOKEN` → random string. Used to auth the daily-digest cron endpoint.
4. Deploy. Copy the assigned URL — you'll need it for the frontend, e.g. `https://career-os-api.onrender.com`

## 4. Deploy the frontend (Render Static Site)

1. Render dashboard → **New + → Static Site** → same repo
2. Settings:
   - **Root Directory**: `frontend`
   - **Build Command**: `yarn install && yarn build`
   - **Publish Directory**: `build`
3. Environment Variable:
   - `REACT_APP_BACKEND_URL` → your backend URL from step 3 (e.g. `https://career-os-api.onrender.com`)
   - **Important**: CRA bakes `REACT_APP_*` vars at build time. After changing this var you MUST trigger a fresh deploy.
4. Add a **Rewrite Rule** so React Router works on refresh:
   ```
   Source: /*    Destination: /index.html    Action: Rewrite
   ```

## 5. Update CORS

After the frontend URL is known, update the backend env var:
```
CORS_ORIGINS=https://career-os-web.onrender.com
```
Trigger a backend redeploy.

## 6. Stripe webhook (production)

Once live:
1. Stripe dashboard → Developers → Webhooks → **+ Add endpoint**
2. URL: `https://career-os-api.onrender.com/api/webhook/stripe`
3. Events: `checkout.session.completed`, `payment_intent.succeeded`
4. Copy the signing secret if you swap to a real Stripe key (Emergent proxy handles signatures for `sk_test_emergent`).

## 6b. Daily digest cron (free external cron)

Once live, register at https://cron-job.org (free) and add a job:
- URL: `https://career-os-api.onrender.com/api/internal/run-daily-digest`
- Method: `POST`
- Schedule: daily at 09:00 in your target timezone
- Headers: `X-Cron-Token: <whatever you set in CRON_TOKEN env>`

Render's free tier sleeps after 15min — the cron POST wakes it up. Acceptable for a daily job.

## 7. Google OAuth — ⚠️ MUST READ

The current auth flow uses **`https://auth.emergentagent.com`** as the OAuth host (Emergent-managed Google login). It is **unconfirmed** whether this service accepts redirect URLs from non-Emergent domains.

**Two paths**:

### Path A — Test first (10 min)
After deploying to Render, click Sign in. If the Google flow completes and you land on `/dashboard`, you're done.

### Path B — Swap to direct Google OAuth (~1 hour)
If Path A fails:
1. Create OAuth credentials at https://console.cloud.google.com → Credentials → OAuth Client ID (Web)
2. Add your Render frontend URL to Authorized redirect URIs
3. Install: `pip install google-auth google-auth-oauthlib`
4. Replace `auth.py` Emergent OAuth flow with direct Google OAuth — most of the logic (cookie, session, MongoDB user upsert) stays identical. Only the `/session-data` exchange swaps to Google's `/oauth2/v4/token` and `/oauth2/v3/userinfo`. The `AuthService` abstraction in `auth.py` was built for exactly this.

---

## 8. Deployment readiness checklist

- [ ] GitHub repo pushed and up to date
- [ ] MongoDB Atlas cluster provisioned + connection string copied
- [ ] Backend deployed, returns 200 on `/api/`
- [ ] `EMERGENT_LLM_KEY` set — verify with `POST /api/jobs/{id}/match`
- [ ] Frontend deployed, loads landing page
- [ ] `REACT_APP_BACKEND_URL` points to backend
- [ ] CORS_ORIGINS includes frontend URL — Sign in works
- [ ] Stripe `/billing/checkout` returns valid Stripe URL
- [ ] Webhook endpoint receives Stripe events (test with `stripe trigger checkout.session.completed`)
- [ ] Free-tier gating works: `/api/me/usage` returns correct quota
- [ ] PDF upload works: `/api/profile/upload-cv` returns parsed profile
- [ ] Job ingest works: `POST /api/jobs/ingest` pulls real Remotive jobs

---

## Known limitations on Render

1. **Emergent Stripe proxy** — `sk_test_emergent` proxies through `integrations.emergentagent.com`. This works from any host but means real Stripe payments require swapping to a real `sk_live_...` key.
2. **`emergentintegrations` library** — installs from a custom index URL. The build command includes the flag. If Render's pip cache misses the package, fall back to `pip install -r requirements.txt && pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`.
3. **MongoDB indexes** — for production, create indexes on:
   ```js
   db.users.createIndex({ email: 1 }, { unique: true })
   db.users.createIndex({ user_id: 1 }, { unique: true })
   db.user_sessions.createIndex({ session_token: 1 }, { unique: true })
   db.user_sessions.createIndex({ expires_at: 1 })
   db.jobs.createIndex({ source_url: 1 })
   db.applications.createIndex({ user_id: 1, job_id: 1 })
   db.match_usage.createIndex({ user_id: 1, month: 1 }, { unique: true })
   db.payment_transactions.createIndex({ session_id: 1 }, { unique: true })
   ```
