#!/bin/bash

# NanoDesigner Production Smoke Tests
set -e

echo "🧪 NanoDesigner Production Smoke Tests"
echo "======================================"

NAMESPACE="nanodesigner"
API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:3000}"
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_test "Running: $test_name"
    
    if eval "$test_command"; then
        echo -e "${GREEN}  ✓ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}  ✗ FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Setup port forwarding if needed
setup_port_forwarding() {
    if [[ "$API_URL" == *"localhost"* ]] || [[ "$API_URL" == *"127.0.0.1"* ]]; then
        log_info "Setting up port forwarding for API..."
        kubectl port-forward svc/api 8000:8000 -n $NAMESPACE &
        API_PORT_FORWARD_PID=$!
        sleep 3
    fi
    
    if [[ "$WEB_URL" == *"localhost"* ]] || [[ "$WEB_URL" == *"127.0.0.1"* ]]; then
        log_info "Setting up port forwarding for Web..."
        kubectl port-forward svc/web 3000:3000 -n $NAMESPACE &
        WEB_PORT_FORWARD_PID=$!
        sleep 3
    fi
}

# Cleanup port forwarding
cleanup_port_forwarding() {
    if [ ! -z "$API_PORT_FORWARD_PID" ]; then
        kill $API_PORT_FORWARD_PID 2>/dev/null || true
    fi
    if [ ! -z "$WEB_PORT_FORWARD_PID" ]; then
        kill $WEB_PORT_FORWARD_PID 2>/dev/null || true
    fi
}

# Infrastructure tests
test_infrastructure() {
    log_info "Testing Infrastructure Components..."
    
    run_test "PostgreSQL is running" \
        "kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].status.phase}' | grep -q Running"
    
    run_test "Redis is running" \
        "kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].status.phase}' | grep -q Running"
    
    run_test "Qdrant is running" \
        "kubectl get pods -n $NAMESPACE -l app=qdrant -o jsonpath='{.items[0].status.phase}' | grep -q Running"
    
    run_test "API pods are running" \
        "kubectl get pods -n $NAMESPACE -l app=api -o jsonpath='{.items[*].status.phase}' | grep -q Running"
    
    run_test "Web pods are running" \
        "kubectl get pods -n $NAMESPACE -l app=web -o jsonpath='{.items[*].status.phase}' | grep -q Running"
}

# API health tests
test_api_health() {
    log_info "Testing API Health..."
    
    run_test "API health endpoint responds" \
        "curl -f -s --max-time $TIMEOUT $API_URL/health > /dev/null"
    
    run_test "API ready endpoint responds" \
        "curl -f -s --max-time $TIMEOUT $API_URL/health/ready > /dev/null"
    
    run_test "API returns valid JSON health status" \
        "curl -s --max-time $TIMEOUT $API_URL/health | jq -e '.status == \"healthy\"' > /dev/null"
    
    run_test "API OpenAPI docs are accessible" \
        "curl -f -s --max-time $TIMEOUT $API_URL/docs > /dev/null"
    
    run_test "API metrics endpoint responds" \
        "curl -f -s --max-time $TIMEOUT $API_URL/metrics > /dev/null"
}

# API functionality tests
test_api_functionality() {
    log_info "Testing API Functionality..."
    
    # Test render endpoint (mock request)
    run_test "Render endpoint accepts requests" \
        "curl -f -s --max-time $TIMEOUT -X POST $API_URL/render \
         -H 'Content-Type: application/json' \
         -d '{\"project_id\":\"test\",\"prompts\":{\"instruction\":\"test logo\"}}' > /dev/null"
    
    # Test ingest endpoint
    run_test "Ingest endpoint is accessible" \
        "curl -f -s --max-time $TIMEOUT -X POST $API_URL/ingest/text \
         -H 'Content-Type: application/json' \
         -d '{\"project_id\":\"test\",\"content\":\"test content\"}' > /dev/null"
    
    # Test canon endpoint
    run_test "Canon endpoint is accessible" \
        "curl -f -s --max-time $TIMEOUT -X POST $API_URL/canon/derive \
         -H 'Content-Type: application/json' \
         -d '{\"project_id\":\"test\",\"assets\":[]}' > /dev/null"
}

# Web application tests
test_web_application() {
    log_info "Testing Web Application..."
    
    run_test "Web app homepage loads" \
        "curl -f -s --max-time $TIMEOUT $WEB_URL > /dev/null"
    
    run_test "Web app returns HTML content" \
        "curl -s --max-time $TIMEOUT $WEB_URL | grep -q '<html'"
    
    run_test "Web app has correct title" \
        "curl -s --max-time $TIMEOUT $WEB_URL | grep -q '<title>.*NanoDesigner.*</title>'"
    
    run_test "Web app dashboard is accessible" \
        "curl -f -s --max-time $TIMEOUT $WEB_URL/dashboard > /dev/null"
    
    run_test "Web app sign-in page is accessible" \
        "curl -f -s --max-time $TIMEOUT $WEB_URL/sign-in > /dev/null"
}

# Database connectivity tests
test_database_connectivity() {
    log_info "Testing Database Connectivity..."
    
    run_test "PostgreSQL accepts connections" \
        "kubectl exec -n $NAMESPACE deployment/postgres -- pg_isready -U postgres"
    
    run_test "Redis accepts connections" \
        "kubectl exec -n $NAMESPACE deployment/redis -- redis-cli ping | grep -q PONG"
    
    run_test "Qdrant API is responsive" \
        "kubectl exec -n $NAMESPACE deployment/qdrant -- curl -f http://localhost:6333/ > /dev/null"
}

# Performance tests
test_performance() {
    log_info "Testing Performance..."
    
    run_test "API responds within 5 seconds" \
        "time curl -f -s --max-time 5 $API_URL/health > /dev/null"
    
    run_test "Web app loads within 10 seconds" \
        "time curl -f -s --max-time 10 $WEB_URL > /dev/null"
    
    # Load test with multiple concurrent requests
    run_test "API handles 10 concurrent requests" \
        "for i in {1..10}; do curl -f -s --max-time $TIMEOUT $API_URL/health & done; wait"
}

# Security tests
test_security() {
    log_info "Testing Security..."
    
    run_test "API has security headers" \
        "curl -I -s --max-time $TIMEOUT $API_URL/health | grep -q 'X-Content-Type-Options'"
    
    run_test "Web app has security headers" \
        "curl -I -s --max-time $TIMEOUT $WEB_URL | grep -q 'X-Frame-Options'"
    
    run_test "API rejects malformed requests" \
        "! curl -f -s --max-time $TIMEOUT -X POST $API_URL/render \
         -H 'Content-Type: application/json' \
         -d 'invalid json' > /dev/null"
}

# Integration tests
test_integration() {
    log_info "Testing Integration..."
    
    # Test that web app can communicate with API
    run_test "Web app can reach API" \
        "kubectl exec -n $NAMESPACE deployment/web -- curl -f -s http://api:8000/health > /dev/null"
    
    # Test that API can reach databases
    run_test "API can reach PostgreSQL" \
        "kubectl exec -n $NAMESPACE deployment/api -- python -c 'import asyncpg; print(\"OK\")'"
    
    run_test "API can reach Redis" \
        "kubectl exec -n $NAMESPACE deployment/api -- python -c 'import redis; print(\"OK\")'"
}

# Generate test report
generate_report() {
    echo ""
    echo "🏁 Test Results Summary"
    echo "======================"
    echo "Total Tests: $TESTS_TOTAL"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! System is ready for production.${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed. Please review and fix issues before production deployment.${NC}"
        return 1
    fi
}

# Main function
main() {
    # Trap to ensure cleanup
    trap cleanup_port_forwarding EXIT
    
    case "${1:-all}" in
        "infra")
            test_infrastructure
            ;;
        "api")
            setup_port_forwarding
            test_api_health
            test_api_functionality
            ;;
        "web")
            setup_port_forwarding
            test_web_application
            ;;
        "db")
            test_database_connectivity
            ;;
        "perf")
            setup_port_forwarding
            test_performance
            ;;
        "security")
            setup_port_forwarding
            test_security
            ;;
        "integration")
            test_integration
            ;;
        "all")
            setup_port_forwarding
            test_infrastructure
            test_database_connectivity
            test_api_health
            test_api_functionality
            test_web_application
            test_performance
            test_security
            test_integration
            ;;
        *)
            echo "Usage: $0 {infra|api|web|db|perf|security|integration|all}"
            echo ""
            echo "Commands:"
            echo "  infra       - Test infrastructure components"
            echo "  api         - Test API health and functionality"
            echo "  web         - Test web application"
            echo "  db          - Test database connectivity"
            echo "  perf        - Test performance"
            echo "  security    - Test security headers and validation"
            echo "  integration - Test component integration"
            echo "  all         - Run all tests (default)"
            exit 1
            ;;
    esac
    
    generate_report
}

# Run main function
main "$@"
