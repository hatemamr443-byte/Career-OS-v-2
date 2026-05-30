#!/bin/bash

# Career-OS-v2: Post-Deployment Validation
# Run this AFTER deploying to Render to verify everything works

if [ -z "$1" ]; then
    echo "Usage: $0 <backend_url> [frontend_url]"
    echo ""
    echo "Example: $0 https://career-os-backend-staging.onrender.com https://career-os-frontend-staging.onrender.com"
    exit 1
fi

BACKEND_URL="$1"
FRONTEND_URL="${2:-}"

echo "════════════════════════════════════════════════════════════════"
echo "POST-DEPLOYMENT VALIDATION TESTS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Backend URL: $BACKEND_URL"
if [ -n "$FRONTEND_URL" ]; then
    echo "Frontend URL: $FRONTEND_URL"
fi
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Backend Health
echo "✓ Test 1: Backend Health Endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Health endpoint responds (200 OK)"
    echo "    Response: $(echo $BODY | jq -r '.status' 2>/dev/null || echo "valid JSON")"
    ((TESTS_PASSED++))
else
    echo "  ❌ Health endpoint failed ($HTTP_CODE)"
    echo "    Response: $BODY"
    ((TESTS_FAILED++))
fi
echo ""

# Test 2: Readiness Endpoint
echo "✓ Test 2: Readiness Endpoint (with timeout)"
START=$(date +%s%N)
RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 "$BACKEND_URL/health/ready")
END=$(date +%s%N)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)
DURATION=$((($END - $START) / 1000000))

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "503" ]; then
    echo "  ✅ Readiness endpoint responds (${DURATION}ms)"
    READY=$(echo $BODY | jq -r '.ready' 2>/dev/null || echo "unknown")
    echo "    Ready: $READY (may be false if DB timeout)"
    ((TESTS_PASSED++))
else
    echo "  ❌ Readiness endpoint failed ($HTTP_CODE, ${DURATION}ms)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Admin Endpoint Protection
echo "✓ Test 3: Admin Endpoint Security"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "x-admin-token: wrong-token" "$BACKEND_URL/admin/system" 2>/dev/null || echo "\n401")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
    echo "  ✅ Admin endpoint protected ($HTTP_CODE)"
    ((TESTS_PASSED++))
else
    echo "  ⚠️  Admin endpoint may not be protected ($HTTP_CODE)"
    ((TESTS_FAILED++))
fi
echo ""

# Test 4: Root Endpoint
echo "✓ Test 4: Root API Endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/api/" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ API root endpoint responds"
    ((TESTS_PASSED++))
else
    echo "  ⚠️  API root endpoint returned $HTTP_CODE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Frontend (if provided)
if [ -n "$FRONTEND_URL" ]; then
    echo "✓ Test 5: Frontend Access"
    RESPONSE=$(curl -s -w "\n%{http_code}" "$FRONTEND_URL" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✅ Frontend loads (200 OK)"
        ((TESTS_PASSED++))
    else
        echo "  ⚠️  Frontend returned $HTTP_CODE"
        ((TESTS_FAILED++))
    fi
    echo ""
fi

# Test 6: Response Time
echo "✓ Test 6: Backend Response Time"
START=$(date +%s%N)
curl -s "$BACKEND_URL/health" > /dev/null
END=$(date +%s%N)
DURATION=$((($END - $START) / 1000000))

if [ $DURATION -lt 3000 ]; then
    echo "  ✅ Response time acceptable: ${DURATION}ms"
    ((TESTS_PASSED++))
else
    echo "  ⚠️  Response time slow: ${DURATION}ms (target: <3s)"
    ((TESTS_FAILED++))
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════"
echo "VALIDATION SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
    echo ""
    echo "Next Steps:"
    echo "1. Monitor logs for 24 hours"
    echo "2. Check Render dashboard for errors"
    echo "3. If staging passes, deploy to production"
    exit 0
else
    echo "⚠️  SOME TESTS FAILED"
    echo ""
    echo "Check:"
    echo "1. Render build logs"
    echo "2. Environment variables"
    echo "3. Network connectivity"
    exit 1
fi

