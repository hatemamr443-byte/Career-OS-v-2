#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════"
echo "  CAREER-OS-V2: AUTOMATED RENDER DEPLOYMENT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "❌ Render CLI not found. Install it:"
    echo "   npm install -g render-cli"
    echo ""
    echo "   Or use Render web dashboard: https://dashboard.render.com"
    exit 1
fi

echo "✅ Render CLI found"
echo ""

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "❌ ERROR: backend/.env not found"
    echo "   Please create it with credentials from env.secrets"
    exit 1
fi

echo "✅ Environment file found"
echo ""

# Load env vars
export $(cat backend/.env | grep -v '^#' | xargs)

echo "════════════════════════════════════════════════════════════════"
echo "  DEPLOYMENT CONFIGURATION"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "GitHub Repo:        https://github.com/hatemamr443-byte/Career-OS-v-2"
echo "Branch:             main"
echo "Backend Service:    career-os-backend-staging"
echo "Frontend Service:   career-os-frontend-staging"
echo "MongoDB URL:        ${MONGO_URL:0:40}..."
echo "Stripe Key:         ${STRIPE_SECRET_KEY:0:20}..."
echo "Environment:        ${ENVIRONMENT}"
echo ""

read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  DEPLOYING BACKEND"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Create backend service
echo "Creating backend service..."
cat > /tmp/backend-service.yaml << 'EOFYAML'
name: career-os-backend-staging
repo: https://github.com/hatemamr443-byte/Career-OS-v-2
branch: main
buildCommand: pip install --upgrade pip && pip install -r backend/requirements.txt
startCommand: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
envVars:
  - name: MONGO_URL
    fromFile: backend/.env
  - name: DB_NAME
    value: career_os
  - name: STRIPE_SECRET_KEY
    fromFile: backend/.env
  - name: EMERGENT_LLM_KEY
    fromFile: backend/.env
  - name: ANTHROPIC_API_KEY
    fromFile: backend/.env
  - name: OPENAI_API_KEY
    fromFile: backend/.env
  - name: GEMINI_API_KEY
    fromFile: backend/.env
  - name: RESEND_API_KEY
    fromFile: backend/.env
  - name: CRON_TOKEN
    fromFile: backend/.env
  - name: ADMIN_TOKEN
    fromFile: backend/.env
  - name: ENVIRONMENT
    value: staging
  - name: CORS_ORIGINS
    value: "*"
healthCheckPath: /health
EOFYAML

echo "✅ Backend service config created"
echo ""
echo "📋 TO DEPLOY ON RENDER.COM:"
echo "   1. Go to https://dashboard.render.com"
echo "   2. Click 'New+' → 'Web Service'"
echo "   3. Connect GitHub repo: hatemamr443-byte/Career-OS-v-2"
echo "   4. Fill in:"
echo "      - Name: career-os-backend-staging"
echo "      - Build: pip install --upgrade pip && pip install -r backend/requirements.txt"
echo "      - Start: cd backend && uvicorn server:app --host 0.0.0.0 --port \$PORT"
echo "      - Health path: /health"
echo "   5. Add environment variables (copy from backend/.env)"
echo "   6. Click Deploy"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  DEPLOYING FRONTEND"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "📋 TO DEPLOY FRONTEND ON RENDER.COM:"
echo "   1. Go to https://dashboard.render.com"
echo "   2. Click 'New+' → 'Static Site'"
echo "   3. Connect GitHub repo: hatemamr443-byte/Career-OS-v-2"
echo "   4. Fill in:"
echo "      - Name: career-os-frontend-staging"
echo "      - Build: cd frontend && npm ci && npm run build"
echo "      - Publish: frontend/build"
echo "   5. Add environment variables:"
echo "      - REACT_APP_BACKEND_URL=https://career-os-backend-staging.onrender.com"
echo "      - REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_..."
echo "   6. Click Deploy"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  VERIFICATION STEPS"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "Waiting for deployment to complete..."
echo "(This takes 5-15 minutes)"
echo ""

# Wait for backend to be ready (max 20 minutes)
BACKEND_URL="https://career-os-backend-staging.onrender.com"
MAX_ATTEMPTS=120
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
        echo "✅ Backend is up!"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 10)) -eq 0 ]; then
        echo "⏳ Still waiting... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    fi
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Backend failed to start within 20 minutes"
    echo "   Check Render logs: https://dashboard.render.com"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  TESTING DEPLOYMENT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 1: Health endpoint
echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s "$BACKEND_URL/health")
if echo "$HEALTH" | grep -q "ok"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    echo "   Response: $HEALTH"
fi

# Test 2: Readiness endpoint
echo "2️⃣  Testing readiness endpoint..."
READY=$(curl -s "$BACKEND_URL/health/ready")
if echo "$READY" | grep -q "ready"; then
    echo "   ✅ Readiness check passed"
else
    echo "   ❌ Readiness check failed"
    echo "   Response: $READY"
fi

# Test 3: Admin protection
echo "3️⃣  Testing admin endpoint protection..."
ADMIN_WRONG=$(curl -s -H "x-admin-token: WRONG" "$BACKEND_URL/admin/system" -w "%{http_code}")
if echo "$ADMIN_WRONG" | grep -q "403"; then
    echo "   ✅ Admin protection working"
else
    echo "   ⚠️  Admin endpoint response: $ADMIN_WRONG"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Backend URL:  $BACKEND_URL"
echo "Frontend URL: https://career-os-frontend-staging.onrender.com"
echo ""
echo "Next steps:"
echo "  1. Monitor Render logs for 24 hours"
echo "  2. Test trial activation (should fail on 2nd attempt)"
echo "  3. Test checkout flow with Stripe test card"
echo "  4. Once validated, deploy to production"
echo ""

