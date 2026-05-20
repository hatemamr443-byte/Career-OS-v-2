# 🔐 SETUP_SECRETS.md — Career OS Secret Management

## Overview

Real `.env` files are **never stored inside this repository**.
Encrypted backups live in `secure-backup/` which is excluded from git.

---

## 1. Restore Encrypted Env Backups Locally

You need OpenSSL installed (pre-installed on macOS/Linux).

```bash
# Decrypt backend .env
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in secure-backup/backend.env.enc \
  -out backend/.env

# Decrypt frontend .env
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in secure-backup/frontend.env.enc \
  -out frontend/.env
```

You will be prompted for the backup password.
The password is stored in `secure-backup/BACKUP_PASSWORD.txt` (keep it safe — store in Bitwarden or 1Password).

---

## 2. Configure Render Environment Variables

Never commit `.env` files to Git. On Render, set variables via the Dashboard:

**Path:** Render Dashboard → Service → Environment → Add Environment Variable

### Backend required variables:

| Variable | Source |
|---|---|
| `MONGO_URL` | MongoDB Atlas → Connect → Drivers |
| `CORS_ORIGINS` | Your frontend Render URL (e.g. `https://career-os-frontend.onrender.com`) |
| `EMERGENT_LLM_KEY` | From your Emergent account |
| `ENVIRONMENT` | `production` |

### Frontend required variables:

| Variable | Source |
|---|---|
| `REACT_APP_BACKEND_URL` | Your backend Render URL (e.g. `https://career-os-backend.onrender.com`) |

---

## 3. Re-encrypt After Rotating Credentials

When you change a credential, re-encrypt and replace the backup:

```bash
# Re-encrypt backend .env after editing it
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
  -in backend/.env \
  -out secure-backup/backend.env.enc

# Re-encrypt frontend .env after editing it
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 \
  -in frontend/.env \
  -out secure-backup/frontend.env.enc
```

Use the **same password** (from BACKUP_PASSWORD.txt) or generate a new one.

---

## 4. Rotate Credentials Safely

1. Generate new key/token from the relevant provider
2. Update `backend/.env` or `frontend/.env` locally
3. Re-encrypt (step 3 above)
4. Update the variable in Render Dashboard
5. Trigger a manual redeploy on Render
6. Verify the service is healthy at `/health`
7. Revoke the old key from the provider

---

## 5. What Is Never Committed to Git

Per `.gitignore`:
- `backend/.env` and `frontend/.env`
- Any `*.env.*` (except `.env.example`)
- `secure-backup/` folder
- `*.enc` files
- `BACKUP_PASSWORD.txt`

