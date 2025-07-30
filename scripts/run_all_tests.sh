#!/bin/bash
# Master test runner script for AutoGen platform
# Runs all test suites with proper setup and teardown

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULTS_DIR"

# Log file
LOG_FILE="$RESULTS_DIR/test-run.log"

# Function to print colored output
print_status() {
    echo -e "${2}${1}${NC}" | tee -a "$LOG_FILE"
}

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local check_type=$2
    local max_attempts=30
    local attempt=0
    
    print_status "Checking health of $service..." "$YELLOW"
    
    while [ $attempt -lt $max_attempts ]; do
        case "$check_type" in
            "rabbitmq")
                if docker exec rabbitmq rabbitmqctl status > /dev/null 2>&1; then
                    print_status "✅ $service is healthy" "$GREEN"
                    return 0
                fi
                ;;
            "redis")
                if docker exec redis redis-cli ping > /dev/null 2>&1; then
                    print_status "✅ $service is healthy" "$GREEN"
                    return 0
                fi
                ;;
            http:*)
                local url=${check_type#http:}
                if curl -f -s "$url" > /dev/null; then
                    print_status "✅ $service is healthy" "$GREEN"
                    return 0
                fi
                ;;
        esac
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_status "❌ $service failed health check after $max_attempts attempts" "$RED"
    return 1
}

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local output_file="$RESULTS_DIR/${suite_name}-results.xml"
    
    print_status "\n🧪 Running $suite_name tests..." "$BLUE"
    
    if eval "$test_command" > "$RESULTS_DIR/${suite_name}.log" 2>&1; then
        print_status "✅ $suite_name tests passed" "$GREEN"
        echo "PASSED" > "$RESULTS_DIR/${suite_name}.status"
        return 0
    else
        print_status "❌ $suite_name tests failed" "$RED"
        echo "FAILED" > "$RESULTS_DIR/${suite_name}.status"
        return 1
    fi
}

# Main test execution
main() {
    print_status "🚀 AutoGen Platform Test Runner" "$BLUE"
    print_status "================================" "$BLUE"
    print_status "Test results will be saved to: $RESULTS_DIR\n" "$YELLOW"
    
    # 1. Pre-flight checks
    print_status "1️⃣ Running pre-flight checks..." "$BLUE"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_status "❌ Docker is not installed" "$RED"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_status "❌ Docker Compose is not installed" "$RED"
        exit 1
    fi
    
    # Check disk space (need at least 5GB)
    available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        print_status "❌ Insufficient disk space (need at least 5GB, have ${available_space}GB)" "$RED"
        exit 1
    fi
    
    print_status "✅ Pre-flight checks passed" "$GREEN"
    
    # 2. Clean up any existing containers
    print_status "\n2️⃣ Cleaning up existing containers..." "$BLUE"
    docker-compose down -v 2>/dev/null || true
    print_status "✅ Cleanup complete" "$GREEN"
    
    # 3. Build services
    print_status "\n3️⃣ Building Docker images..." "$BLUE"
    if ! docker-compose build > "$RESULTS_DIR/docker-build.log" 2>&1; then
        print_status "❌ Docker build failed" "$RED"
        cat "$RESULTS_DIR/docker-build.log"
        exit 1
    fi
    print_status "✅ Docker images built successfully" "$GREEN"
    
    # 4. Start core services
    print_status "\n4️⃣ Starting core services..." "$BLUE"
    docker-compose up -d rabbitmq redis
    sleep 5
    
    # Check RabbitMQ
    check_service_health "RabbitMQ" "rabbitmq" || exit 1
    
    # Check Redis
    check_service_health "Redis" "redis" || exit 1
    
    # 5. Start application services
    print_status "\n5️⃣ Starting application services..." "$BLUE"
    docker-compose up -d api-gateway core-engine control-board
    
    # Wait for services to be ready
    check_service_health "API Gateway" "http:http://localhost:8000/health" || exit 1
    check_service_health "Control Board" "http:http://localhost:3001" || exit 1
    
    # 6. Run test suites
    print_status "\n6️⃣ Running test suites..." "$BLUE"
    
    # Track overall test status
    all_tests_passed=true
    
    # Unit tests
    if ! run_test_suite "unit" "docker-compose run --rm test-runner pytest tests/unit -v --junitxml=/results/unit-results.xml"; then
        all_tests_passed=false
    fi
    
    # Integration tests
    if ! run_test_suite "integration" "docker-compose run --rm test-runner pytest tests/integration -v --junitxml=/results/integration-results.xml"; then
        all_tests_passed=false
    fi
    
    # API tests
    if ! run_test_suite "api" "docker-compose run --rm test-runner python scripts/test_platform.py"; then
        all_tests_passed=false
    fi
    
    # E2E tests
    if ! run_test_suite "e2e" "docker-compose run --rm test-runner pytest tests/e2e -v --junitxml=/results/e2e-results.xml"; then
        all_tests_passed=false
    fi
    
    # Control board tests
    if ! run_test_suite "ui" "cd control-board && npm test"; then
        all_tests_passed=false
    fi
    
    # Performance tests (optional)
    if [ "${RUN_PERF_TESTS:-false}" = "true" ]; then
        if ! run_test_suite "performance" "docker-compose run --rm test-runner locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 30s --html /results/performance-report.html"; then
            all_tests_passed=false
        fi
    fi
    
    # 7. Collect logs and artifacts
    print_status "\n7️⃣ Collecting logs and artifacts..." "$BLUE"
    
    # Service logs
    docker-compose logs > "$RESULTS_DIR/docker-compose.log" 2>&1
    
    # Copy test artifacts from containers
    docker cp test-runner:/results/. "$RESULTS_DIR/" 2>/dev/null || true
    
    # Generate coverage report
    if [ -f "$RESULTS_DIR/coverage.xml" ]; then
        print_status "📊 Coverage report generated" "$GREEN"
    fi
    
    # 8. Generate HTML report
    print_status "\n8️⃣ Generating test report..." "$BLUE"
    generate_html_report
    
    # 9. Cleanup
    print_status "\n9️⃣ Cleaning up..." "$BLUE"
    if [ "${KEEP_CONTAINERS:-false}" != "true" ]; then
        docker-compose down
        print_status "✅ Containers stopped and removed" "$GREEN"
    else
        print_status "ℹ️  Containers kept running (KEEP_CONTAINERS=true)" "$YELLOW"
    fi
    
    # 10. Summary
    print_status "\n📊 Test Summary" "$BLUE"
    print_status "===============" "$BLUE"
    
    for suite in unit integration api e2e ui; do
        if [ -f "$RESULTS_DIR/${suite}.status" ]; then
            status=$(cat "$RESULTS_DIR/${suite}.status")
            if [ "$status" = "PASSED" ]; then
                print_status "✅ $suite: PASSED" "$GREEN"
            else
                print_status "❌ $suite: FAILED" "$RED"
            fi
        fi
    done
    
    print_status "\n📁 Test results saved to: $RESULTS_DIR" "$YELLOW"
    print_status "📄 HTML report: $RESULTS_DIR/report.html" "$YELLOW"
    
    # Exit with appropriate code
    if [ "$all_tests_passed" = true ]; then
        print_status "\n✅ All tests passed!" "$GREEN"
        exit 0
    else
        print_status "\n❌ Some tests failed!" "$RED"
        exit 1
    fi
}

# Function to generate HTML report
generate_html_report() {
    cat > "$RESULTS_DIR/report.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>AutoGen Platform Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f0f0f0; padding: 15px; border-radius: 5px; }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .suite { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .logs { background: #f8f8f8; padding: 10px; font-family: monospace; font-size: 12px; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>AutoGen Platform Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Generated: <script>document.write(new Date().toLocaleString());</script></p>
        <table>
            <tr>
                <th>Test Suite</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
EOF
    
    # Add test results to HTML
    for suite in unit integration api e2e ui; do
        if [ -f "$RESULTS_DIR/${suite}.status" ]; then
            status=$(cat "$RESULTS_DIR/${suite}.status")
            class=$([ "$status" = "PASSED" ] && echo "passed" || echo "failed")
            echo "<tr><td>$suite</td><td class='$class'>$status</td><td><a href='${suite}.log'>View Log</a></td></tr>" >> "$RESULTS_DIR/report.html"
        fi
    done
    
    cat >> "$RESULTS_DIR/report.html" << 'EOF'
        </table>
    </div>
    
    <h2>Service Health</h2>
    <ul>
        <li>API Gateway: <span class="passed">✓ Healthy</span></li>
        <li>RabbitMQ: <span class="passed">✓ Healthy</span></li>
        <li>Redis: <span class="passed">✓ Healthy</span></li>
        <li>Control Board: <span class="passed">✓ Healthy</span></li>
    </ul>
    
    <h2>Artifacts</h2>
    <ul>
        <li><a href="docker-compose.log">Docker Compose Logs</a></li>
        <li><a href="coverage.xml">Coverage Report (XML)</a></li>
        <li><a href="performance-report.html">Performance Report</a></li>
    </ul>
</body>
</html>
EOF
}

# Run main function
main "$@"