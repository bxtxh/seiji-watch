#!/bin/bash

# ===================================================
# Docker Logs Viewer Script
# ===================================================
# Usage: ./logs.sh [service] [options]
# Options: -f (follow), -n <lines> (tail lines)

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

# Parse arguments
SERVICE=$1
FOLLOW=""
TAIL="100"

# Shift first argument if it's a service name
if [ ! -z "$SERVICE" ]; then
    shift
fi

# Parse remaining options
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n|--tail)
            TAIL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

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

# Function to show service menu
show_service_menu() {
    echo "====================================================="
    echo "Select a service to view logs:"
    echo "====================================================="
    echo ""
    echo "Core Services:"
    echo "  1) api-gateway      - API Gateway"
    echo "  2) web-frontend     - Web Frontend"
    echo "  3) data-processor   - Data Processor"
    echo ""
    echo "Worker Services:"
    echo "  4) diet-scraper     - Diet Website Scraper"
    echo "  5) stt-worker       - Speech-to-Text Worker"
    echo "  6) vector-store     - Vector Store Service"
    echo "  7) notifications    - Notifications Worker"
    echo ""
    echo "Infrastructure:"
    echo "  8) postgres         - PostgreSQL Database"
    echo "  9) redis            - Redis Cache"
    echo ""
    echo "Tools:"
    echo "  10) adminer         - Database Admin UI"
    echo "  11) mailhog         - Email Testing"
    echo ""
    echo "  0) all              - All services"
    echo "  q) quit             - Exit"
    echo ""
    read -p "Enter selection: " selection
    
    case $selection in
        1) SERVICE="api-gateway" ;;
        2) SERVICE="web-frontend" ;;
        3) SERVICE="data-processor" ;;
        4) SERVICE="diet-scraper" ;;
        5) SERVICE="stt-worker" ;;
        6) SERVICE="vector-store" ;;
        7) SERVICE="notifications-worker" ;;
        8) SERVICE="postgres" ;;
        9) SERVICE="redis" ;;
        10) SERVICE="adminer" ;;
        11) SERVICE="mailhog" ;;
        0) SERVICE="" ;;
        q|Q) exit 0 ;;
        *) 
            echo -e "${RED}Invalid selection${NC}"
            exit 1
            ;;
    esac
}

# If no service specified, show menu
if [ -z "$SERVICE" ] && [ -z "$1" ]; then
    show_service_menu
fi

# Header
echo ""
echo "====================================================="
if [ -z "$SERVICE" ]; then
    echo "Viewing logs for ALL services"
else
    echo "Viewing logs for: $SERVICE"
fi
echo "====================================================="
echo ""

# Build log command
LOG_CMD="$DOCKER_COMPOSE logs --tail $TAIL $FOLLOW"

if [ ! -z "$SERVICE" ]; then
    LOG_CMD="$LOG_CMD $SERVICE"
fi

# Add timestamp and colors
LOG_CMD="$LOG_CMD --timestamps"

# Show command being executed
echo -e "${BLUE}ℹ${NC} Executing: $LOG_CMD"
echo ""

# Execute log command
$LOG_CMD

# If not following, show help
if [ -z "$FOLLOW" ]; then
    echo ""
    echo "====================================================="
    echo "Tips:"
    echo "  • To follow logs:    ./logs.sh $SERVICE -f"
    echo "  • To see more lines: ./logs.sh $SERVICE -n 500"
    echo "  • To see all logs:   ./logs.sh all"
    echo "====================================================="
fi