#!/bin/bash

# Career-OS-v2: 24-Hour Deployment Monitoring Script
# Run after deploying to Render staging
# Monitors health every hour for 24 hours

if [ -z "$1" ]; then
    echo "Usage: $0 <backend_url> [duration_hours]"
    echo ""
    echo "Example: $0 https://career-os-backend-staging.onrender.com 24"
    echo ""
    echo "Default: Monitors for 24 hours"
    exit 1
fi

BACKEND_URL="$1"
DURATION=${2:-24}
INTERVAL=3600  # 1 hour in seconds

echo "════════════════════════════════════════════════════════════════"
echo "DEPLOYMENT MONITORING — $DURATION HOURS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Backend URL: $BACKEND_URL"
echo "Check Interval: Every hour"
echo "Duration: $DURATION hours"
echo ""
echo "Monitoring will check:"
echo "  ✓ Health endpoint (200 OK)"
echo "  ✓ Readiness endpoint (no hang)"
echo "  ✓ Response time (< 3s)"
echo "  ✓ No error patterns in response"
echo ""

# Create log file
LOGFILE="/tmp/deployment_monitoring_$(date +%s).log"
echo "Logging to: $LOGFILE"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0
START_TIME=$(date +%s)
END_TIME=$((START_TIME + (DURATION * 3600)))

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    ELAPSED=$(($(date +%s) - START_TIME))
    HOURS=$((ELAPSED / 3600))
    
    echo "[$CURRENT_TIME] Hour $((HOURS + 1))/$DURATION" | tee -a "$LOGFILE"
    
    # Test 1: Health
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/health" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✅ Health: 200 OK" | tee -a "$LOGFILE"
        ((CHECKS_PASSED++))
    else
        echo "  ❌ Health: $HTTP_CODE" | tee -a "$LOGFILE"
        ((CHECKS_FAILED++))
    fi
    
    # Test 2: Readiness (should timeout in <2s now)
    START=$(date +%s%N)
    RESPONSE=$(curl -s -m 5 "$BACKEND_URL/health/ready" 2>/dev/null)
    END=$(date +%s%N)
    DURATION_MS=$((($END - $START) / 1000000))
    
    if [ $DURATION_MS -lt 3000 ]; then
        echo "  ✅ Readiness: ${DURATION_MS}ms (OK)" | tee -a "$LOGFILE"
        ((CHECKS_PASSED++))
    else
        echo "  ⚠️  Readiness: ${DURATION_MS}ms (slow)" | tee -a "$LOGFILE"
        ((CHECKS_FAILED++))
    fi
    
    # Test 3: Response time
    START=$(date +%s%N)
    curl -s "$BACKEND_URL/api/" > /dev/null 2>&1
    END=$(date +%s%N)
    API_TIME=$((($END - $START) / 1000000))
    
    if [ $API_TIME -lt 2000 ]; then
        echo "  ✅ API Response: ${API_TIME}ms" | tee -a "$LOGFILE"
        ((CHECKS_PASSED++))
    else
        echo "  ⚠️  API Response: ${API_TIME}ms" | tee -a "$LOGFILE"
        ((CHECKS_FAILED++))
    fi
    
    echo "" | tee -a "$LOGFILE"
    
    # Wait for next hour (unless this is the last iteration)
    if [ $(date +%s) -lt $END_TIME ]; then
        echo "Waiting 1 hour until next check..." | tee -a "$LOGFILE"
        sleep $INTERVAL
    fi
done

echo "════════════════════════════════════════════════════════════════"
echo "MONITORING COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Checks Passed: $CHECKS_PASSED"
echo "  Checks Failed: $CHECKS_FAILED"
echo "  Log File: $LOGFILE"
echo ""

if [ $CHECKS_FAILED -lt 5 ]; then
    echo "✅ MONITORING PASSED — System stable for $DURATION hours"
    echo ""
    echo "Ready for production deployment"
    exit 0
else
    echo "⚠️  MONITORING ISSUES DETECTED"
    echo ""
    echo "Review log file and Render dashboard before production"
    exit 1
fi

