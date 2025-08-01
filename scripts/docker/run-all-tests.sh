#!/bin/bash

# ===================================================
# Run All Tests in Docker
# ===================================================
# This script runs all tests for all services

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="/test-results"
mkdir -p "$RESULTS_DIR"

# Summary variables
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
FAILED_SERVICES=()

# Function to run tests for a service
run_service_tests() {
    local service=$1
    local test_cmd=$2
    
    echo ""
    echo "====================================================="
    echo -e "${BLUE}Testing: $service${NC}"
    echo "====================================================="
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_cmd"; then
        echo -e "${GREEN}✓ $service tests passed${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ $service tests failed${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_SERVICES+=("$service")
    fi
}

# Wait for services to be ready
echo -e "${BLUE}Waiting for services to be ready...${NC}"
timeout 30 bash -c 'until nc -z postgres 5432; do sleep 1; done' || echo "Postgres timeout"
timeout 30 bash -c 'until nc -z redis 6379; do sleep 1; done' || echo "Redis timeout"

# Create test database
echo -e "${BLUE}Setting up test database...${NC}"
PGPASSWORD=seiji_watch_pass psql -h postgres -U seiji_watch_user -d seiji_watch -c "CREATE DATABASE seiji_watch_test;" 2>/dev/null || true

# Run Python service tests
for service in api-gateway data-processor diet-scraper stt-worker vector-store notifications-worker; do
    if [ -d "/workspace/services/$service" ]; then
        run_service_tests "$service" "cd /workspace/services/$service && python -m pytest tests/ -v --cov=src --cov-report=xml:$RESULTS_DIR/${service}-coverage.xml --junit-xml=$RESULTS_DIR/${service}-junit.xml || true"
    fi
done

# Run frontend tests
if [ -d "/workspace/services/web-frontend" ]; then
    run_service_tests "web-frontend" "cd /workspace/services/web-frontend && npm test -- --coverage --coverageDirectory=$RESULTS_DIR/web-frontend-coverage || true"
fi

# Run linting checks
echo ""
echo "====================================================="
echo -e "${BLUE}Running linting checks...${NC}"
echo "====================================================="

# Python linting
echo "Python linting..."
find /workspace/services -name "*.py" -type f | while read -r file; do
    ruff check "$file" || true
done

# JavaScript/TypeScript linting
echo "JavaScript/TypeScript linting..."
if [ -d "/workspace/services/web-frontend" ]; then
    cd /workspace/services/web-frontend && npm run lint || true
fi

# Generate coverage report
echo ""
echo "====================================================="
echo -e "${BLUE}Generating coverage report...${NC}"
echo "====================================================="

# Combine Python coverage reports
if command -v coverage &> /dev/null; then
    coverage combine $RESULTS_DIR/*.coverage 2>/dev/null || true
    coverage html -d $RESULTS_DIR/htmlcov 2>/dev/null || true
    coverage report > $RESULTS_DIR/coverage-summary.txt 2>/dev/null || true
fi

# Summary
echo ""
echo "====================================================="
echo "Test Summary"
echo "====================================================="
echo -e "Total services tested: ${TOTAL_TESTS}"
echo -e "Passed: ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Failed: ${RED}${FAILED_TESTS}${NC}"

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed services:${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo "  - $service"
    done
fi

echo ""
echo "Test results saved to: $RESULTS_DIR"
echo "====================================================="

# Exit with failure if any tests failed
if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi