#!/bin/bash

# Career-OS-v2: Pre-Deployment Verification Checklist
# Run this BEFORE deploying to Render to ensure everything is ready

echo "════════════════════════════════════════════════════════════════"
echo "PRE-DEPLOYMENT VERIFICATION CHECKLIST"
echo "════════════════════════════════════════════════════════════════"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

# Check 1: Git is clean
echo "✓ Check 1: Git Status"
if git status --short | grep -q "^"; then
    echo "  ⚠️  UNCOMMITTED CHANGES DETECTED"
    git status --short
    ((CHECKS_FAILED++))
else
    echo "  ✅ No uncommitted changes"
    ((CHECKS_PASSED++))
fi
echo ""

# Check 2: Backend files exist
echo "✓ Check 2: Backend Files"
if [ -f "backend/server.py" ] && [ -f "backend/db.py" ]; then
    echo "  ✅ Backend files present"
    ((CHECKS_PASSED++))
else
    echo "  ❌ Backend files missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 3: Frontend files exist
echo "✓ Check 3: Frontend Files"
if [ -f "frontend/package.json" ] && [ -d "frontend/src" ]; then
    echo "  ✅ Frontend files present"
    ((CHECKS_PASSED++))
else
    echo "  ❌ Frontend files missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 4: Environment template exists
echo "✓ Check 4: Environment Template"
if [ -f "backend/.env.example" ]; then
    echo "  ✅ Environment template exists"
    ((CHECKS_PASSED++))
else
    echo "  ❌ Environment template missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 5: Requirements file exists
echo "✓ Check 5: Python Requirements"
if [ -f "backend/requirements.txt" ]; then
    echo "  ✅ requirements.txt exists"
    echo "    Packages: $(wc -l < backend/requirements.txt) listed"
    ((CHECKS_PASSED++))
else
    echo "  ❌ requirements.txt missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 6: Latest commits include fixes
echo "✓ Check 6: Git Commits"
if git log --oneline -3 | grep -q "fix(backend)"; then
    echo "  ✅ Backend fixes committed"
    git log --oneline -3 | head -1
    ((CHECKS_PASSED++))
else
    echo "  ⚠️  No recent backend fixes in last 3 commits"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 7: Memory files exist
echo "✓ Check 7: Memory Files"
if [ -f "PROJECT_MEMORY_SESSION_SUMMARY.md" ] && [ -f "SESSION_HANDOFF.md" ]; then
    echo "  ✅ Memory files present"
    ((CHECKS_PASSED++))
else
    echo "  ⚠️  Memory files missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Check 8: Deployment guide exists
echo "✓ Check 8: Deployment Guide"
if [ -f "RENDER_DEPLOYMENT_EXECUTION.md" ]; then
    echo "  ✅ Deployment guide exists"
    ((CHECKS_PASSED++))
else
    echo "  ⚠️  Deployment guide missing"
    ((CHECKS_FAILED++))
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════"
echo "SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo "Checks Passed: $CHECKS_PASSED"
echo "Checks Failed: $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED — READY FOR RENDER DEPLOYMENT"
    echo ""
    echo "Next Steps:"
    echo "1. Go to https://dashboard.render.com"
    echo "2. See RENDER_DEPLOYMENT_EXECUTION.md for detailed steps"
    exit 0
else
    echo "⚠️  SOME CHECKS FAILED — FIX BEFORE DEPLOYING"
    exit 1
fi

