#!/bin/bash

# Week 1 Reality Check - Basic Functionality
set -e

echo "🔍 WEEK 1 REALITY CHECK - BASIC FUNCTIONALITY"
echo "============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=8

check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo ""
echo "1. Frontend Build Check"
echo "----------------------"
cd apps/web
if npm run build > /dev/null 2>&1; then
    check_result 0 "Frontend builds without errors"
else
    check_result 1 "Frontend build has errors"
fi
cd ../..

echo ""
echo "2. Backend Test Check"
echo "--------------------"
cd api
if python -m pytest --tb=no -q > /dev/null 2>&1; then
    check_result 0 "All backend tests pass"
else
    FAILED_TESTS=$(python -m pytest --tb=no -q 2>&1 | grep "FAILED" | wc -l)
    check_result 1 "Backend has $FAILED_TESTS failing tests"
fi
cd ..

echo ""
echo "3. API Health Check"
echo "------------------"
# Check if API is already running on port 8001, otherwise start on 8002
if curl -f -s http://localhost:8001/healthz > /dev/null 2>&1; then
    check_result 0 "API health endpoint responds (port 8001)"
    API_PID=""
else
    # Start API in background for testing
    cd api
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 > /dev/null 2>&1 &
    API_PID=$!
    sleep 5
    
    if curl -f -s http://localhost:8002/healthz > /dev/null 2>&1; then
        check_result 0 "API health endpoint responds (port 8002)"
    else
        check_result 1 "API health endpoint not responding"
    fi
fi

# Cleanup
if [ -n "$API_PID" ]; then
    kill $API_PID 2>/dev/null || true
fi
cd ..

echo ""
echo "4. Database Connection Check"
echo "---------------------------"
cd api
if python basic_db.py > /dev/null 2>&1; then
    check_result 0 "Database connection working"
else
    check_result 1 "Database connection failed"
fi
cd ..

echo ""
echo "5. Authentication Flow Check"
echo "---------------------------"
cd api
if python basic_auth.py > /dev/null 2>&1; then
    check_result 0 "Authentication flow working"
else
    check_result 1 "Authentication flow failed"
fi
cd ..

echo ""
echo "6. File Upload Check"
echo "-------------------"
cd api
if python basic_upload.py > /dev/null 2>&1; then
    check_result 0 "File upload working"
else
    check_result 1 "File upload failed"
fi
cd ..

echo ""
echo "7. Frontend Startup Check"
echo "------------------------"
cd apps/web
npm run dev > /dev/null 2>&1 &
WEB_PID=$!
sleep 10

if curl -f -s http://localhost:3000/ > /dev/null 2>&1; then
    check_result 0 "Frontend starts and serves pages"
else
    check_result 1 "Frontend not starting properly"
fi

# Cleanup
kill $WEB_PID 2>/dev/null || true
cd ../..

echo ""
echo "8. Core Services Check"
echo "---------------------"
cd api
if python basic_services.py > /dev/null 2>&1; then
    check_result 0 "Core services working"
else
    check_result 1 "Core services failed"
fi
cd ..

echo ""
echo "📊 WEEK 1 RESULTS"
echo "=================="
echo -e "Passed: ${GREEN}$PASS_COUNT/$TOTAL_CHECKS${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT/$TOTAL_CHECKS${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}🎉 WEEK 1 COMPLETE - READY FOR WEEK 2${NC}"
    exit 0
else
    echo -e "${RED}❌ WEEK 1 INCOMPLETE - FIX FAILURES BEFORE WEEK 2${NC}"
    echo ""
    echo "REQUIRED ACTIONS:"
    echo "1. Fix all failing checks above"
    echo "2. Re-run this script until 0 failures"
    echo "3. Only then proceed to Week 2"
    exit 1
fi
