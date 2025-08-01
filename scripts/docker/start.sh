#!/bin/bash

# ===================================================
# Docker Services Start Script
# ===================================================
# Usage: ./start.sh [profile]
# Profiles: core, workers, tools, full, prod

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

# Default profile
PROFILE=${1:-core}

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Header
echo "====================================================="
echo "Diet Issue Tracker - Docker Services Startup"
echo "====================================================="
echo ""

# Validate environment first
print_info "Validating environment variables..."
if ! "$SCRIPT_DIR/validate-env.sh"; then
    print_error "Environment validation failed"
    exit 1
fi

echo ""

# Check Docker Compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    print_error "Docker Compose is not installed"
    exit 1
fi

# Profile descriptions
case "$PROFILE" in
    core)
        print_info "Starting CORE services (API + Frontend + Database)"
        SERVICES="postgres redis api-gateway web-frontend"
        ;;
    workers)
        print_info "Starting WORKER services"
        SERVICES="postgres redis diet-scraper stt-worker vector-store notifications-worker data-processor"
        ;;
    tools)
        print_info "Starting DEVELOPMENT TOOLS"
        SERVICES="postgres redis adminer mailhog redis-commander pgadmin"
        ;;
    full)
        print_info "Starting ALL services"
        SERVICES=""  # Empty means all services
        ;;
    prod)
        print_info "Starting PRODUCTION configuration"
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        SERVICES=""
        ;;
    test)
        print_info "Starting TEST environment"
        SERVICES="postgres redis test-runner"
        ;;
    *)
        print_error "Invalid profile: $PROFILE"
        echo "Available profiles: core, workers, tools, full, prod, test"
        exit 1
        ;;
esac

# Change to project root
cd "$PROJECT_ROOT"

# Set compose files
if [ -z "$COMPOSE_FILES" ]; then
    if [ "$PROFILE" = "prod" ]; then
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    else
        COMPOSE_FILES="-f docker-compose.yml"
    fi
fi

# Build images if needed
print_info "Building Docker images..."
$DOCKER_COMPOSE $COMPOSE_FILES build --parallel

# Pull latest base images
print_info "Pulling latest base images..."
$DOCKER_COMPOSE $COMPOSE_FILES pull --ignore-pull-failures

# Start services
print_info "Starting services with profile: $PROFILE"
if [ "$PROFILE" = "prod" ]; then
    $DOCKER_COMPOSE $COMPOSE_FILES up -d $SERVICES
else
    COMPOSE_PROFILES=$PROFILE $DOCKER_COMPOSE $COMPOSE_FILES up -d $SERVICES
fi

# Wait for services to be healthy
print_info "Waiting for services to be healthy..."
sleep 5

# Check service status
print_info "Checking service status..."
$DOCKER_COMPOSE $COMPOSE_FILES ps

echo ""
echo "====================================================="

# Service URLs based on profile
case "$PROFILE" in
    core|full)
        print_success "Services are running!"
        echo ""
        echo "Service URLs:"
        echo "  • Frontend:    http://localhost:3000"
        echo "  • API Gateway: http://localhost:8000"
        echo "  • API Docs:    http://localhost:8000/docs"
        ;;
    tools|full)
        if [ "$PROFILE" = "tools" ] || [ "$PROFILE" = "full" ]; then
            echo "  • Adminer:     http://localhost:8080"
            echo "  • Mailhog:     http://localhost:8025"
            echo "  • Redis Cmd:   http://localhost:8081"
            echo "  • PgAdmin:     http://localhost:8082"
        fi
        ;;
esac

echo ""
echo "Commands:"
echo "  • View logs:    ./scripts/docker/logs.sh [service]"
echo "  • Stop services: docker compose --profile $PROFILE down"
echo "  • Reset data:   ./scripts/docker/reset.sh"
echo ""

# Check if running on core profile
if [ "$PROFILE" = "core" ]; then
    print_warning "Only core services are running. To start all services, run:"
    echo "    ./scripts/docker/start.sh full"
fi

echo "====================================================="
print_success "Startup complete!"