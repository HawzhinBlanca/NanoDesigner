#!/bin/bash

# Week 2 Reality Check - Core Features & Security
# This script validates all Week 2 implementations

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
TOTAL_CHECKS=12

# Function to check results
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((PASS_COUNT++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
    fi
}

echo -e "${BLUE}🔍 WEEK 2 REALITY CHECK - CORE FEATURES & SECURITY${NC}"
echo "=============================================================="

echo ""
echo "1. Enhanced Security System Check"
echo "--------------------------------"
cd api
if python test_enhanced_security.py > /dev/null 2>&1; then
    check_result 0 "Enhanced security system working"
else
    check_result 1 "Enhanced security system failed"
fi
cd ..

echo ""
echo "2. Tenant Isolation System Check"
echo "-------------------------------"
cd api
if python test_tenant_isolation.py > /dev/null 2>&1; then
    check_result 0 "Tenant isolation system working"
else
    check_result 1 "Tenant isolation system failed"
fi
cd ..

echo ""
echo "3. Enhanced OpenRouter Integration Check"
echo "--------------------------------------"
cd api
if python test_enhanced_openrouter.py > /dev/null 2>&1; then
    check_result 0 "Enhanced OpenRouter integration working"
else
    check_result 1 "Enhanced OpenRouter integration failed"
fi
cd ..

echo ""
echo "4. Monitoring & Metrics System Check"
echo "-----------------------------------"
cd api
if python test_monitoring.py > /dev/null 2>&1; then
    check_result 0 "Monitoring & metrics system working"
else
    check_result 1 "Monitoring & metrics system failed"
fi
cd ..

echo ""
echo "5. Content Policy Enforcement Check"
echo "----------------------------------"
cd api
python -c "
from app.core.enhanced_security import security_manager
result = security_manager.scan_render_request('Create explicit violent content', ['javascript:alert(1)'])
assert result.threat_level.value == 'blocked'
print('Content policy enforcement working')
" > /dev/null 2>&1
check_result $? "Content policy blocks malicious content"

echo ""
echo "6. Per-Org Isolation Check"
echo "-------------------------"
cd api
python -c "
from app.core.tenant_isolation import isolation_manager, TenantContext, IsolationLevel
tenant1 = isolation_manager.create_tenant_context('org1', 'user1')
tenant2 = isolation_manager.create_tenant_context('org2', 'user2')
path1 = isolation_manager.get_storage_path(tenant1, 'file.jpg')
path2 = isolation_manager.get_storage_path(tenant2, 'file.jpg')
assert path1 != path2
assert 'org1' in path1 and 'org2' in path2
print('Per-org isolation working')
" > /dev/null 2>&1
check_result $? "Per-org isolation creates separate paths"

echo ""
echo "7. Cost Tracking Check"
echo "---------------------"
cd api
python -c "
from app.services.enhanced_openrouter import CostTracker
from decimal import Decimal
tracker = CostTracker()
cost = tracker.calculate_cost('openai/gpt-4', {'prompt_tokens': 1000, 'completion_tokens': 500})
assert cost > Decimal('0')
print('Cost tracking working')
" > /dev/null 2>&1
check_result $? "AI cost tracking calculates costs"

echo ""
echo "8. SynthID Verification Check"
echo "----------------------------"
cd api
python -c "
import asyncio
from app.services.enhanced_openrouter import SynthIDVerifier
async def test():
    verifier = SynthIDVerifier()
    result = await verifier.verify_content('test content', 'openai/gpt-4')
    assert 'is_ai_generated' in result
    print('SynthID verification working')
asyncio.run(test())
" > /dev/null 2>&1
check_result $? "SynthID verification system working"

echo ""
echo "9. Prometheus Metrics Check"
echo "--------------------------"
cd api
python -c "
from app.core.monitoring import metrics_collector
metrics_collector.record_api_request('POST', '/test', 200, 1.0, 'test-org')
output = metrics_collector.get_prometheus_metrics()
assert b'api_requests_total' in output
print('Prometheus metrics working')
" > /dev/null 2>&1
check_result $? "Prometheus metrics generation working"

echo ""
echo "10. Security Alert System Check"
echo "------------------------------"
cd api
python -c "
from app.core.monitoring import metrics_collector, AlertLevel
initial_count = len(metrics_collector.alerts)
metrics_collector.create_alert(AlertLevel.ERROR, 'Test alert', 'test')
assert len(metrics_collector.alerts) > initial_count
print('Alert system working')
" > /dev/null 2>&1
check_result $? "Security alert system working"

echo ""
echo "11. Budget Management Check"
echo "-------------------------"
cd api
python -c "
from app.services.enhanced_openrouter import CostTracker, CostBudget
from app.core.tenant_isolation import TenantContext, IsolationLevel
from decimal import Decimal
tracker = CostTracker()
tenant = TenantContext('test-org', 'user1', IsolationLevel.ISOLATED, [])
budget = CostBudget(Decimal('10.00'), Decimal('100.00'), Decimal('1.00'))
tracker.set_budget(tenant, budget)
assert tracker.check_budget_limits(tenant, Decimal('0.50'))
assert not tracker.check_budget_limits(tenant, Decimal('2.00'))
print('Budget management working')
" > /dev/null 2>&1
check_result $? "Budget management enforces limits"

echo ""
echo "12. Integration Test - Full Security Pipeline"
echo "-------------------------------------------"
cd api
python -c "
from app.core.enhanced_security import security_manager
from app.core.tenant_isolation import isolation_manager
from app.core.monitoring import metrics_collector

# Create tenant
tenant = isolation_manager.create_tenant_context('integration-test', 'user1')

# Test security scan
result = security_manager.scan_render_request('Create a beautiful landscape', ['https://api.openai.com/test'])
assert result.threat_level.value == 'safe'

# Test metrics recording
initial_events = len([a for a in metrics_collector.alerts if a.component == 'security'])
metrics_collector.record_security_event('test_event', 'safe', tenant.org_id)

print('Full security pipeline working')
" > /dev/null 2>&1
check_result $? "Full security pipeline integration working"

cd ..

echo ""
echo -e "${BLUE}📊 WEEK 2 RESULTS${NC}"
echo "=================="
echo -e "Passed: ${GREEN}$PASS_COUNT/$TOTAL_CHECKS${NC}"
echo -e "Failed: ${RED}$((TOTAL_CHECKS - PASS_COUNT))/$TOTAL_CHECKS${NC}"

if [ $PASS_COUNT -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}🎉 WEEK 2 COMPLETE - ALL CORE FEATURES WORKING${NC}"
    echo ""
    echo -e "${GREEN}✅ Enhanced Security System${NC}"
    echo -e "${GREEN}✅ Per-Organization Isolation${NC}" 
    echo -e "${GREEN}✅ AI Integration with Cost Tracking${NC}"
    echo -e "${GREEN}✅ Comprehensive Monitoring & Metrics${NC}"
    echo -e "${GREEN}✅ Content Policy Enforcement${NC}"
    echo -e "${GREEN}✅ SynthID Verification${NC}"
    echo -e "${GREEN}✅ Budget Management${NC}"
    echo -e "${GREEN}✅ Prometheus Integration${NC}"
    echo ""
    echo -e "${GREEN}🚀 READY FOR WEEK 3 - PRODUCTION HARDENING${NC}"
    exit 0
else
    echo -e "${RED}❌ WEEK 2 INCOMPLETE - FIX FAILURES BEFORE WEEK 3${NC}"
    echo ""
    echo "REQUIRED ACTIONS:"
    echo "1. Fix all failing checks above"
    echo "2. Re-run this script until 0 failures"
    echo "3. Only then proceed to Week 3"
    exit 1
fi