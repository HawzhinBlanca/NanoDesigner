#!/bin/bash

# Week 3 Reality Check - Production Readiness
set -e

echo "🔍 WEEK 3 REALITY CHECK - PRODUCTION READINESS"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=20

check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "   Details: $3"
    fi
}

echo ""
echo "1. Complete E2E User Flow Test"
echo "==============================="

# Test complete user journey
cd apps/web
if npm run test:e2e > /dev/null 2>&1; then
    check_result 0 "E2E user flow tests pass"
else
    check_result 1 "E2E user flow tests failing" "Run 'npm run test:e2e' to see failures"
fi
cd ..

echo ""
echo "2. All Test Suites Validation"
echo "============================="

# Frontend tests
cd apps/web
if npm test > /dev/null 2>&1; then
    check_result 0 "Frontend unit tests pass"
else
    check_result 1 "Frontend unit tests failing" "Run 'npm test' to see failures"
fi
cd ..

# Backend tests
cd api
PYTEST_OUTPUT=$(python -m pytest --tb=short -q 2>&1)
if echo "$PYTEST_OUTPUT" | grep -q "failed"; then
    FAILED_COUNT=$(echo "$PYTEST_OUTPUT" | grep "failed" | sed 's/.*\([0-9]\+\) failed.*/\1/')
    check_result 1 "Backend tests failing" "$FAILED_COUNT tests failed"
else
    check_result 0 "Backend tests pass"
fi
cd ..

echo ""
echo "3. Performance Benchmarks"
echo "========================"

# Lighthouse performance test
cd apps/web
if command -v lighthouse > /dev/null 2>&1; then
    npm run build > /dev/null 2>&1
    npm run start > /dev/null 2>&1 &
    WEB_PID=$!
    sleep 10
    
    LIGHTHOUSE_SCORE=$(lighthouse http://localhost:3000 --only-categories=performance --output=json --quiet | jq '.categories.performance.score * 100')
    kill $WEB_PID 2>/dev/null || true
    
    if [ "$LIGHTHOUSE_SCORE" -ge 90 ]; then
        check_result 0 "Lighthouse performance ≥90" "Score: $LIGHTHOUSE_SCORE"
    else
        check_result 1 "Lighthouse performance <90" "Score: $LIGHTHOUSE_SCORE"
    fi
else
    check_result 1 "Lighthouse not installed" "Install with: npm install -g lighthouse"
fi
cd ..

# Bundle size check
cd apps/web
BUNDLE_SIZE=$(du -sk .next/static/chunks/*.js 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "999")
if [ "$BUNDLE_SIZE" -le 200 ]; then
    check_result 0 "Bundle size ≤200KB" "Size: ${BUNDLE_SIZE}KB"
else
    check_result 1 "Bundle size >200KB" "Size: ${BUNDLE_SIZE}KB"
fi
cd ..

echo ""
echo "4. Security Validation"
echo "====================="

# Check for security vulnerabilities
cd apps/web
if npm audit --audit-level=high > /dev/null 2>&1; then
    check_result 0 "No high/critical npm vulnerabilities"
else
    VULN_COUNT=$(npm audit --audit-level=high --json | jq '.metadata.vulnerabilities.high + .metadata.vulnerabilities.critical' 2>/dev/null || echo "unknown")
    check_result 1 "High/critical npm vulnerabilities found" "$VULN_COUNT vulnerabilities"
fi
cd ..

cd api
if pip-audit > /dev/null 2>&1; then
    check_result 0 "No Python security vulnerabilities"
else
    check_result 1 "Python security vulnerabilities found" "Run 'pip-audit' to see details"
fi
cd ..

# Input validation test
echo "Testing input validation..."
check_result 1 "Input validation tests not implemented" "Need to implement malicious input tests"

# Tenant isolation test
echo "Testing tenant isolation..."
check_result 1 "Tenant isolation tests not implemented" "Need to implement cross-tenant access tests"

echo ""
echo "5. Production Deployment Test"
echo "============================"

# Docker build test
if docker build -f docker/api.Dockerfile -t nanodesigner/api:test . > /dev/null 2>&1; then
    check_result 0 "API Docker image builds"
else
    check_result 1 "API Docker image build fails" "Check Dockerfile syntax and dependencies"
fi

if docker build -f docker/web.Dockerfile -t nanodesigner/web:test . > /dev/null 2>&1; then
    check_result 0 "Web Docker image builds"
else
    check_result 1 "Web Docker image build fails" "Check Dockerfile syntax and dependencies"
fi

# Kubernetes manifest validation
if command -v kubectl > /dev/null 2>&1; then
    if kubectl apply --dry-run=client -f k8s/ > /dev/null 2>&1; then
        check_result 0 "Kubernetes manifests valid"
    else
        check_result 1 "Kubernetes manifests invalid" "Check YAML syntax and resource definitions"
    fi
else
    check_result 1 "kubectl not available" "Install kubectl to test K8s manifests"
fi

echo ""
echo "6. API Performance Test"
echo "======================"

# Start API for testing
cd api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /dev/null 2>&1 &
API_PID=$!
sleep 5

# Test API response time
RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8001/health)
if (( $(echo "$RESPONSE_TIME < 0.5" | bc -l) )); then
    check_result 0 "API response time <500ms" "Time: ${RESPONSE_TIME}s"
else
    check_result 1 "API response time ≥500ms" "Time: ${RESPONSE_TIME}s"
fi

# Cleanup
kill $API_PID 2>/dev/null || true
cd ..

echo ""
echo "7. Load Testing"
echo "=============="

# Basic load test (would need proper load testing tool)
check_result 1 "Load testing not implemented" "Need to implement 100 concurrent user test"

echo ""
echo "8. Monitoring & Alerting"
echo "======================="

# Check monitoring endpoints
check_result 1 "Monitoring not fully implemented" "Need Prometheus metrics and Grafana dashboards"

echo ""
echo "9. Backup & Recovery"
echo "==================="

# Test backup procedures
check_result 1 "Backup procedures not tested" "Need to test database backup/restore"

echo ""
echo "10. Ship Gate Criteria Validation"
echo "================================="

# All ship gate criteria from TASKS.md
SHIP_GATES=(
    "render_e2e_contract_tests"
    "synthid_declared_not_verified"
    "tenant_isolation_enforced"
    "upload_av_mime_exif_gated"
    "budget_caps_functional"
    "playwright_e2e_complete"
    "lighthouse_perf_90_bundle_200kb"
)

for gate in "${SHIP_GATES[@]}"; do
    check_result 1 "Ship gate: $gate" "Not implemented/tested yet"
done

echo ""
echo "📊 FINAL PRODUCTION READINESS RESULTS"
echo "====================================="
echo -e "Passed: ${GREEN}$PASS_COUNT/$TOTAL_CHECKS${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT/$TOTAL_CHECKS${NC}"

PASS_PERCENTAGE=$((PASS_COUNT * 100 / TOTAL_CHECKS))
echo -e "Success Rate: $PASS_PERCENTAGE%"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 PRODUCTION READY - ALL CHECKS PASSED${NC}"
    echo "✅ System is ready for production deployment"
    echo "✅ All security requirements met"
    echo "✅ All performance benchmarks achieved"
    echo "✅ All ship gate criteria satisfied"
    exit 0
else
    echo ""
    echo -e "${RED}❌ NOT PRODUCTION READY - $FAIL_COUNT FAILURES${NC}"
    echo ""
    echo "CRITICAL ISSUES TO FIX:"
    echo "1. Fix all failing tests"
    echo "2. Implement missing security features"
    echo "3. Meet performance benchmarks"
    echo "4. Complete all ship gate criteria"
    echo "5. Re-run this script until 0 failures"
    echo ""
    echo -e "${YELLOW}DO NOT DEPLOY TO PRODUCTION UNTIL ALL CHECKS PASS${NC}"
    exit 1
fi
