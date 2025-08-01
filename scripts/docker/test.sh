#!/bin/bash

# ===================================================
# Docker Test Runner Script
# ===================================================
# Usage: ./test.sh [service] [test-args]
# Examples:
#   ./test.sh              # Run all tests
#   ./test.sh api-gateway  # Run API gateway tests
#   ./test.sh web-frontend # Run frontend tests

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# Service to test
SERVICE=${1:-all}
shift || true
TEST_ARGS="$@"

# Check Docker Compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}✗${NC} Docker Compose is not installed"
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Function to run Python tests
run_python_tests() {
    local service=$1
    local container="seiji-watch-${service}"
    
    echo -e "${BLUE}ℹ${NC} Running Python tests for $service..."
    
    # Build the test image
    $DOCKER_COMPOSE build $service
    
    # Run tests
    $DOCKER_COMPOSE run --rm \
        -e ENVIRONMENT=test \
        $service \
        pytest tests/ \
            --verbose \
            --cov=src \
            --cov-report=term-missing \
            --cov-report=html:coverage/${service} \
            $TEST_ARGS
}

# Function to run Node.js tests
run_node_tests() {
    echo -e "${BLUE}ℹ${NC} Running Node.js tests for web-frontend..."
    
    # Build the test image
    $DOCKER_COMPOSE build web-frontend
    
    # Run tests
    $DOCKER_COMPOSE run --rm \
        -e NODE_ENV=test \
        web-frontend \
        npm test -- $TEST_ARGS
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}ℹ${NC} Running E2E tests..."
    
    # Start services
    echo "Starting services for E2E tests..."
    COMPOSE_PROFILES=core $DOCKER_COMPOSE up -d
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Run Playwright tests
    $DOCKER_COMPOSE run --rm \
        -e NODE_ENV=test \
        web-frontend \
        npm run test:e2e -- $TEST_ARGS
    
    # Stop services
    echo "Stopping services..."
    $DOCKER_COMPOSE down
}

# Header
echo "====================================================="
echo "Diet Issue Tracker - Test Runner"
echo "====================================================="
echo ""

# Ensure test database exists
echo -e "${BLUE}ℹ${NC} Ensuring test environment is ready..."
$DOCKER_COMPOSE up -d postgres redis
sleep 5

# Create test database if it doesn't exist
$DOCKER_COMPOSE exec -T postgres psql -U seiji_watch_user -d seiji_watch -c "CREATE DATABASE seiji_watch_test;" 2>/dev/null || true

# Run tests based on service
case "$SERVICE" in
    all)
        echo -e "${BLUE}ℹ${NC} Running all tests..."
        echo ""
        
        # Python services
        for svc in api-gateway data-processor diet-scraper stt-worker vector-store notifications-worker; do
            echo "====================================================="
            echo "Testing: $svc"
            echo "====================================================="
            run_python_tests $svc || true
            echo ""
        done
        
        # Frontend tests
        echo "====================================================="
        echo "Testing: web-frontend"
        echo "====================================================="
        run_node_tests || true
        echo ""
        
        # E2E tests
        echo "====================================================="
        echo "Running E2E tests"
        echo "====================================================="
        run_e2e_tests || true
        ;;
        
    api-gateway|data-processor|diet-scraper|stt-worker|vector-store|notifications-worker)
        run_python_tests $SERVICE
        ;;
        
    web-frontend)
        run_node_tests
        ;;
        
    e2e)
        run_e2e_tests
        ;;
        
    *)
        echo -e "${RED}✗${NC} Unknown service: $SERVICE"
        echo ""
        echo "Available services:"
        echo "  • all                   - Run all tests"
        echo "  • api-gateway           - API Gateway tests"
        echo "  • data-processor        - Data Processor tests"
        echo "  • diet-scraper          - Diet Scraper tests"
        echo "  • stt-worker            - STT Worker tests"
        echo "  • vector-store          - Vector Store tests"
        echo "  • notifications-worker  - Notifications tests"
        echo "  • web-frontend          - Frontend unit tests"
        echo "  • e2e                   - End-to-end tests"
        exit 1
        ;;
esac

# Generate coverage report
if [ -d "coverage" ]; then
    echo ""
    echo "====================================================="
    echo -e "${GREEN}✓${NC} Test execution complete!"
    echo "====================================================="
    echo ""
    echo "Coverage reports generated in: ./coverage/"
    echo ""
    
    # Show coverage summary
    if command -v python3 &> /dev/null; then
        python3 -c "
import os
import json
from pathlib import Path

coverage_dir = Path('coverage')
if coverage_dir.exists():
    print('Coverage Summary:')
    print('-' * 40)
    for service_dir in coverage_dir.iterdir():
        if service_dir.is_dir():
            cov_file = service_dir / '.coverage'
            if cov_file.exists():
                print(f'  • {service_dir.name}: Check coverage/{service_dir.name}/index.html')
    print()
" 2>/dev/null || true
    fi
else
    echo ""
    echo "====================================================="
    echo -e "${GREEN}✓${NC} Tests complete!"
    echo "====================================================="
fi

# Cleanup
echo -e "${BLUE}ℹ${NC} Cleaning up test containers..."
$DOCKER_COMPOSE down

echo ""
echo "Test run finished at: $(date)"