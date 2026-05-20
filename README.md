# Career OS — Canonical Repository (v3.3)

> AI-powered job tracking platform. Built with FastAPI + React + MongoDB Atlas.

---

## Table of Contents

- [Quick Start (Local)](#quick-start-local)
- [Environment Setup](#environment-setup)
- [Render Deployment](#render-deployment)
- [MongoDB Atlas Setup](#mongodb-atlas-setup)
- [Restoring Encrypted Backups](#restoring-encrypted-backups)
- [Dev vs Production Workflow](#dev-vs-production-workflow)
- [Project Structure](#project-structure)

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+ / Yarn
- MongoDB (local or Atlas)

### 1. Clone & setup backend
```bash
git clone https://github.com/YOUR_USERNAME/career-os-canonical.git
cd career-os-canonical

cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt
cp .env.example .env    # then fill in your values
uvicorn server:app --reload --port 8001
```

### 2. Setup frontend
```bash
cd frontend
yarn install
cp .env.example .env    # then fill in your values
yarn start
```

App runs at: `http://localhost:3000`
Backend at: `http://localhost:8001`

---

## Environment Setup

### Backend (`backend/.env`)

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="career_os"
CORS_ORIGINS="http://localhost:3000"
EMERGENT_LLM_KEY=your_emergent_key
ENVIRONMENT=development
CRON_TOKEN=local-dev-token
```

See `backend/.env.example` for full reference.

### Frontend (`frontend/.env`)

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

See `frontend/.env.example` for full reference.

> ⚠️ Never commit real `.env` files. They are excluded by `.gitignore`.

---

## Render Deployment

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Career OS v3.3 canonical"
git remote add origin https://github.com/YOUR_USERNAME/career-os-canonical.git
git push -u origin main
```

### Step 2 — Deploy via Blueprint
1. Go to [render.com](https://render.com)
2. New → **Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` and creates both services automatically

### Step 3 — Set Environment Variables

After services are created, go to each service → **Environment**:

**Backend** (`career-os-backend`):
- `MONGO_URL` → your MongoDB Atlas connection string
- `CORS_ORIGINS` → your frontend Render URL
- `EMERGENT_LLM_KEY` → your key
- `ENVIRONMENT` → `production`

**Frontend** (`career-os-frontend`):
- `REACT_APP_BACKEND_URL` → your backend Render URL

### Step 4 — Redeploy backend
After setting `CORS_ORIGINS`, trigger a **Manual Deploy** on the backend so it picks up the new CORS config.

### Step 5 — Verify
```
GET https://career-os-backend.onrender.com/health
→ {"status": "ok", "db": "connected"}
```

---

## MongoDB Atlas Setup

1. Create account at [cloud.mongodb.com](https://cloud.mongodb.com)
2. New Project → Build a Cluster → **M0 Free Tier**
3. Create Database User (username + strong password)
4. Network Access → Add IP → **0.0.0.0/0** (Allow from anywhere)
5. Connect → Drivers → Copy connection string:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/`
6. Replace `USER`, `PASSWORD`, add `?retryWrites=true&w=majority` at end
7. Paste as `MONGO_URL` in Render backend environment

---

## Restoring Encrypted Backups

Encrypted `.env` backups live in `secure-backup/` (not in git).

```bash
# Restore backend .env
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in secure-backup/backend.env.enc \
  -out backend/.env

# Restore frontend .env
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in secure-backup/frontend.env.enc \
  -out frontend/.env
```

See `SETUP_SECRETS.md` for full credential management guide.

---

## Dev vs Production Workflow

| Concern | Development | Production (Render) |
|---|---|---|
| Backend URL | `http://localhost:8001` | `https://career-os-backend.onrender.com` |
| Frontend URL | `http://localhost:3000` | `https://career-os-frontend.onrender.com` |
| MongoDB | Local `mongod` | MongoDB Atlas M0 Free |
| Secrets | Local `.env` files | Render Dashboard env vars |
| LLM | Emergent key (dev) | Emergent key (prod) |
| CORS | `*` or localhost | Frontend Render URL only |
| ENVIRONMENT | `development` | `production` |

---

## Project Structure

```
career-os-canonical/
├── backend/               # FastAPI app
│   ├── server.py          # Entry point
│   ├── routes_*.py        # Route modules
│   ├── models.py          # Pydantic models
│   ├── llm_service.py     # AI/LLM integrations
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # React (CRA + Craco)
│   ├── src/
│   ├── package.json
│   └── .env.example
├── chrome-extension/      # Browser extension
├── memory/                # Architecture + roadmap docs
│   ├── ARCHITECTURE.md
│   ├── AUDIT.md
│   ├── PRD.md
│   └── ROADMAP.md
├── test_reports/          # Iteration test reports (6-9)
├── tests/                 # Integration tests
├── render.yaml            # Render deploy config
├── SETUP_SECRETS.md       # Credential management guide
└── README.md
```
