#!/bin/bash

# ===================================================
# Docker Shell Access Script
# ===================================================
# Usage: ./shell.sh [service]
# Provides interactive shell access to running containers

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

# Service name
SERVICE=$1

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
    echo "Select a service to access:"
    echo "====================================================="
    echo ""
    
    # Get running containers
    RUNNING_CONTAINERS=$($DOCKER_COMPOSE ps --services 2>/dev/null | sort)
    
    if [ -z "$RUNNING_CONTAINERS" ]; then
        echo -e "${RED}No services are running!${NC}"
        echo ""
        echo "Start services first with: ./scripts/docker/start.sh"
        exit 1
    fi
    
    echo "Running services:"
    echo ""
    
    # Display services with numbers
    i=1
    declare -a services_array
    while IFS= read -r service; do
        services_array[$i]=$service
        printf "  %2d) %-20s\n" $i "$service"
        i=$((i+1))
    done <<< "$RUNNING_CONTAINERS"
    
    echo ""
    echo "   q) quit"
    echo ""
    read -p "Enter selection: " selection
    
    if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
        exit 0
    fi
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -lt "$i" ]; then
        SERVICE=${services_array[$selection]}
    else
        echo -e "${RED}Invalid selection${NC}"
        exit 1
    fi
}

# If no service specified, show menu
if [ -z "$SERVICE" ]; then
    show_service_menu
fi

# Check if service is running
if ! $DOCKER_COMPOSE ps --services | grep -q "^${SERVICE}$"; then
    echo -e "${RED}✗${NC} Service '$SERVICE' is not running"
    echo ""
    echo "Start it with: ./scripts/docker/start.sh"
    exit 1
fi

# Determine the shell based on the service
case "$SERVICE" in
    postgres)
        SHELL_CMD="psql -U seiji_watch_user -d seiji_watch"
        echo -e "${BLUE}ℹ${NC} Connecting to PostgreSQL database..."
        echo "  • Use \\q to exit"
        echo "  • Use \\? for help"
        echo ""
        ;;
    redis)
        SHELL_CMD="redis-cli"
        echo -e "${BLUE}ℹ${NC} Connecting to Redis..."
        echo "  • Use 'exit' to quit"
        echo "  • Use 'help' for commands"
        echo ""
        ;;
    web-frontend)
        SHELL_CMD="/bin/sh"
        echo -e "${BLUE}ℹ${NC} Accessing Node.js container..."
        echo "  • Working directory: /app"
        echo "  • Use 'exit' to quit"
        echo ""
        ;;
    api-gateway|data-processor|diet-scraper|stt-worker|vector-store|notifications-worker)
        SHELL_CMD="/bin/bash"
        echo -e "${BLUE}ℹ${NC} Accessing Python container..."
        echo "  • Working directory: /app"
        echo "  • Python REPL: python"
        echo "  • Use 'exit' to quit"
        echo ""
        
        # For Python services, offer to start Python REPL
        echo "Options:"
        echo "  1) Bash shell"
        echo "  2) Python REPL"
        echo "  3) IPython shell (if available)"
        read -p "Select option [1]: " py_option
        
        case "$py_option" in
            2)
                SHELL_CMD="python"
                ;;
            3)
                SHELL_CMD="ipython || python"
                ;;
            *)
                SHELL_CMD="/bin/bash"
                ;;
        esac
        ;;
    adminer|mailhog|pgadmin|redis-commander)
        echo -e "${YELLOW}⚠${NC} This is a web service. Access it via browser:"
        case "$SERVICE" in
            adminer)
                echo "  URL: http://localhost:8080"
                ;;
            mailhog)
                echo "  URL: http://localhost:8025"
                ;;
            pgadmin)
                echo "  URL: http://localhost:8082"
                ;;
            redis-commander)
                echo "  URL: http://localhost:8081"
                ;;
        esac
        exit 0
        ;;
    *)
        SHELL_CMD="/bin/sh"
        echo -e "${BLUE}ℹ${NC} Accessing container..."
        echo "  • Use 'exit' to quit"
        echo ""
        ;;
esac

# Execute shell
echo "====================================================="
echo -e "${GREEN}Connecting to $SERVICE...${NC}"
echo "====================================================="
echo ""

# Run the shell command
$DOCKER_COMPOSE exec $SERVICE $SHELL_CMD

echo ""
echo -e "${GREEN}✓${NC} Disconnected from $SERVICE"