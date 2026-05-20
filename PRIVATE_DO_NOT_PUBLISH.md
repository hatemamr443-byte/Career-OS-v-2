# ⚠️ PRIVATE ARCHIVE — DO NOT UPLOAD TO PUBLIC GITHUB

> **This archive contains sensitive credentials and active runtime configuration.**
> It is a full-state backup intended **only** for migration, restoration, or
> private storage.

---

## What's in this archive that public repos must never see

This archive includes **real, working** values for some or all of the
following — extracted from the live runtime at the moment of packaging:

* `backend/.env`
  * `EMERGENT_LLM_KEY` — active universal LLM key (Anthropic + OpenAI + Gemini access)
  * `CRON_TOKEN` — daily-email cron auth token
  * Any provider keys present at packaging time
    (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
     `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY`,
     `SENTRY_DSN`, `ADZUNA_*`, `JOOBLE_API_KEY`)
* `frontend/.env`
  * `REACT_APP_BACKEND_URL` — the live deployed backend URL
* All runtime configuration that was active when this archive was sealed.

If any of these leak to a public repository, **rotate them immediately**:

| Key | Where to rotate |
|---|---|
| `EMERGENT_LLM_KEY` | Emergent profile → Universal Key |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/account/keys |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `STRIPE_SECRET_KEY` | https://dashboard.stripe.com/apikeys |
| `RESEND_API_KEY` | https://resend.com/api-keys |
| `SENTRY_DSN` | Sentry project settings (rotate DSN if needed) |

---

## Intended uses

✅ Personal local backup
✅ Restoring the exact working state on a new machine you control
✅ Handover to a co-founder / contractor over **secure** channel
✅ Disaster recovery snapshot

## NOT intended for

❌ Public GitHub / GitLab
❌ Public cloud storage without encryption
❌ Slack / Discord / email attachments
❌ Issue tracker uploads

For public distribution, use the **separate sanitized archive**
(`career-os-public-vX.Y.zip`) which strips every `.env` and substitutes
only `.env.example` placeholders.

---

## Restoring on a fresh machine

```bash
unzip career-os-PRIVATE-v*.zip
cd career-os

# Backend
pip install -r backend/requirements.txt \
  --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
# .env is already present and ready

# Frontend
cd frontend
yarn install
cd ..

# Run
(cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload) &
(cd frontend && yarn start)
```

Health check: `curl http://localhost:8001/health`

---

## Sealing date

This archive reflects the exact working state at the time of packaging.
See file mtimes inside the archive for precise per-file timestamps.

**Treat this archive as you would a password vault.**
