#!/bin/bash

# Smart Graphic Designer API - Load Testing Runner
# This script runs comprehensive load tests against the SGD API

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RESULTS_DIR="${PROJECT_ROOT}/tests/load/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default values
BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT_TOKEN="${JWT_TOKEN:-test-token}"
TEST_TYPE="${TEST_TYPE:-smoke}"
RESULTS_FORMAT="${RESULTS_FORMAT:-json,html}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Load testing runner for Smart Graphic Designer API

OPTIONS:
    -u, --url URL           Base URL for API (default: http://localhost:8000)
    -t, --token TOKEN       JWT token for authentication
    -T, --type TYPE         Test type: smoke|load|stress|spike|endurance (default: smoke)
    -f, --format FORMAT     Output format: json,html,summary (default: json,html)
    -o, --output DIR        Output directory (default: tests/load/results)
    -c, --concurrent N      Number of concurrent users (overrides test type)
    -d, --duration TIME     Test duration (overrides test type)
    -h, --help              Show this help message

TEST TYPES:
    smoke       Quick validation test (5 VUs, 2 minutes)
    load        Normal load test (20-50 VUs, 15 minutes)  
    stress      Stress test to find breaking point (up to 200 VUs, 20 minutes)
    spike       Spike test with sudden load increase (100 VUs spike, 3 minutes)
    endurance   Long-running test for stability (30 VUs, 60 minutes)

EXAMPLES:
    # Run smoke test against local API
    $0 --type smoke

    # Run load test against staging with authentication
    $0 --url https://staging-api.example.com --token \$JWT_TOKEN --type load

    # Run custom stress test with specific parameters
    $0 --type stress --concurrent 100 --duration 10m

    # Generate only HTML report
    $0 --type load --format html
EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if k6 is installed
    if ! command -v k6 &> /dev/null; then
        log_error "k6 is not installed. Please install k6 first:"
        log_error "  macOS: brew install k6"
        log_error "  Linux: sudo apt-get install k6"
        log_error "  Or download from: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
    
    # Check k6 version
    K6_VERSION=$(k6 version | head -n1 | awk '{print $2}')
    log_info "k6 version: ${K6_VERSION}"
    
    # Check if API is accessible
    log_info "Checking API accessibility..."
    if curl -s -f "${BASE_URL}/healthz" >/dev/null; then
        log_success "API is accessible at ${BASE_URL}"
    else
        log_warning "API health check failed. The service might be down or URL incorrect."
        log_warning "Proceeding anyway - k6 will provide detailed error information."
    fi
    
    # Create results directory
    mkdir -p "${RESULTS_DIR}"
    log_info "Results will be saved to: ${RESULTS_DIR}"
}

get_test_config() {
    case "$TEST_TYPE" in
        "smoke")
            K6_OPTIONS="--vus 5 --duration 2m"
            log_info "Running smoke test: 5 VUs for 2 minutes"
            ;;
        "load")
            K6_OPTIONS=""  # Use options from JS file
            log_info "Running load test: Progressive load up to 50 VUs over 20 minutes"
            ;;
        "stress")
            K6_OPTIONS=""  # Use stress scenario from JS file
            log_info "Running stress test: Progressive load up to 200 VUs over 20 minutes"
            ;;
        "spike")
            K6_OPTIONS="--vus 10 --duration 3m --stage 30s:100,1m:100,30s:10"
            log_info "Running spike test: Sudden spike to 100 VUs"
            ;;
        "endurance")
            K6_OPTIONS="--vus 30 --duration 60m"
            log_info "Running endurance test: 30 VUs for 60 minutes"
            ;;
        *)
            log_error "Unknown test type: $TEST_TYPE"
            exit 1
            ;;
    esac
}

run_test() {
    local test_file="${SCRIPT_DIR}/k6-load-test.js"
    local output_file="${RESULTS_DIR}/load-test-${TEST_TYPE}-${TIMESTAMP}"
    
    log_info "Starting load test..."
    log_info "Test type: ${TEST_TYPE}"
    log_info "Base URL: ${BASE_URL}"
    log_info "Output file: ${output_file}"
    
    # Build k6 command
    local k6_cmd="k6 run"
    
    # Add custom options if provided
    if [[ -n "$CONCURRENT_USERS" ]]; then
        k6_cmd+=" --vus $CONCURRENT_USERS"
    fi
    
    if [[ -n "$TEST_DURATION" ]]; then
        k6_cmd+=" --duration $TEST_DURATION"
    fi
    
    # Add default options if no custom ones provided
    if [[ -z "$CONCURRENT_USERS" && -z "$TEST_DURATION" && -n "$K6_OPTIONS" ]]; then
        k6_cmd+=" $K6_OPTIONS"
    fi
    
    # Add output formats
    if [[ "$RESULTS_FORMAT" == *"json"* ]]; then
        k6_cmd+=" --out json=${output_file}.json"
    fi
    
    if [[ "$RESULTS_FORMAT" == *"html"* ]]; then
        # HTML report requires additional setup
        if k6 version | grep -q "xk6-reporter"; then
            k6_cmd+=" --out web-dashboard=${output_file}.html"
        else
            log_warning "HTML output not available. Install xk6-reporter for HTML reports."
        fi
    fi
    
    # Add environment variables
    k6_cmd+=" --env BASE_URL=${BASE_URL}"
    if [[ -n "$JWT_TOKEN" ]]; then
        k6_cmd+=" --env JWT_TOKEN=${JWT_TOKEN}"
    fi
    
    # Add test file
    k6_cmd+=" $test_file"
    
    log_info "Executing: $k6_cmd"
    echo
    
    # Run the test
    if eval $k6_cmd; then
        log_success "Load test completed successfully!"
        
        # Generate summary if requested
        if [[ "$RESULTS_FORMAT" == *"summary"* ]]; then
            generate_summary "$output_file"
        fi
        
        # Print result files
        log_info "Results saved to:"
        find "${RESULTS_DIR}" -name "*${TIMESTAMP}*" -type f | while read -r file; do
            echo "  📄 $file"
        done
        
    else
        log_error "Load test failed!"
        exit 1
    fi
}

generate_summary() {
    local output_file="$1"
    local summary_file="${output_file}_summary.txt"
    
    log_info "Generating test summary..."
    
    cat > "$summary_file" << EOF
# Smart Graphic Designer API - Load Test Summary

**Test Configuration:**
- Test Type: $TEST_TYPE
- Base URL: $BASE_URL  
- Timestamp: $TIMESTAMP
- Duration: $(get_test_duration)

**Key Metrics:**
$(extract_key_metrics "${output_file}.json")

**Performance Analysis:**
$(analyze_performance "${output_file}.json")

**Recommendations:**
$(generate_recommendations "${output_file}.json")

---
Generated on: $(date)
EOF

    log_success "Summary saved to: $summary_file"
}

get_test_duration() {
    case "$TEST_TYPE" in
        "smoke") echo "2 minutes" ;;
        "load") echo "20 minutes" ;;
        "stress") echo "20 minutes" ;;
        "spike") echo "3 minutes" ;;
        "endurance") echo "60 minutes" ;;
        *) echo "Unknown" ;;
    esac
}

extract_key_metrics() {
    local json_file="$1"
    
    if [[ -f "$json_file" ]]; then
        # Use jq to extract key metrics if available
        if command -v jq &> /dev/null; then
            echo "- Total Requests: $(jq -r '.root_group.checks | length' "$json_file" 2>/dev/null || echo 'N/A')"
            echo "- Success Rate: $(jq -r '.root_group.checks[0].passes / (.root_group.checks[0].passes + .root_group.checks[0].fails) * 100' "$json_file" 2>/dev/null || echo 'N/A')%"
            echo "- Average Response Time: $(jq -r '.metrics.http_req_duration.avg' "$json_file" 2>/dev/null || echo 'N/A')ms"
            echo "- 95th Percentile: $(jq -r '.metrics.http_req_duration.p95' "$json_file" 2>/dev/null || echo 'N/A')ms"
        else
            echo "- Install jq for detailed metrics parsing"
        fi
    else
        echo "- Results file not found"
    fi
}

analyze_performance() {
    local json_file="$1"
    echo "- Performance analysis requires manual review of k6 output"
    echo "- Check the detailed JSON results for threshold violations"
    echo "- Review error rates and response time distributions"
}

generate_recommendations() {
    echo "- Monitor API response times during high load"
    echo "- Verify database connection pooling under stress"
    echo "- Consider implementing request queuing for AI operations"
    echo "- Review caching strategies for frequently accessed data"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -t|--token)
            JWT_TOKEN="$2"
            shift 2
            ;;
        -T|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -f|--format)
            RESULTS_FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            RESULTS_DIR="$2"
            shift 2
            ;;
        -c|--concurrent)
            CONCURRENT_USERS="$2"
            shift 2
            ;;
        -d|--duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Smart Graphic Designer API - Load Test Runner"
    log_info "============================================"
    
    check_prerequisites
    get_test_config
    run_test
    
    log_success "Load testing completed!"
    echo
    log_info "Next steps:"
    echo "  1. Review the results in: ${RESULTS_DIR}"
    echo "  2. Check for any threshold violations"
    echo "  3. Analyze response time patterns"
    echo "  4. Monitor system resources during tests"
    echo "  5. Consider scaling recommendations based on results"
}

# Run main function
main "$@"