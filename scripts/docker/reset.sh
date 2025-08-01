#!/bin/bash

# ===================================================
# Docker Environment Reset Script
# ===================================================
# This script completely resets the Docker environment
# WARNING: This will delete all data!

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
FORCE=false
KEEP_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -f, --force         Skip confirmation"
            echo "  --keep-volumes      Keep data volumes"
            echo "  -h, --help          Show this help"
            exit 0
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

# Header
echo "====================================================="
echo -e "${YELLOW}⚠ Docker Environment Reset${NC}"
echo "====================================================="
echo ""

if [ "$KEEP_VOLUMES" = false ]; then
    echo -e "${RED}WARNING: This will delete ALL Docker containers, images, and volumes!${NC}"
    echo "This includes:"
    echo "  • All database data"
    echo "  • All cached data"
    echo "  • All scraped files"
    echo "  • All Docker images (will need to rebuild)"
else
    echo -e "${YELLOW}This will reset containers and images but KEEP data volumes${NC}"
fi

echo ""

# Confirmation
if [ "$FORCE" = false ]; then
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    if [ "$confirmation" != "yes" ]; then
        echo -e "${YELLOW}Reset cancelled${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}ℹ${NC} Starting reset process..."
echo ""

# Step 1: Stop all containers
echo "1. Stopping all containers..."
$DOCKER_COMPOSE --profile full down || true

# Step 2: Remove all containers
echo "2. Removing all project containers..."
docker ps -a --filter "label=com.docker.compose.project=seiji-watch" -q | xargs -r docker rm -f || true

# Step 3: Remove all images
echo "3. Removing all project images..."
docker images --filter "reference=seiji-watch*" -q | xargs -r docker rmi -f || true

# Step 4: Remove volumes (if not keeping)
if [ "$KEEP_VOLUMES" = false ]; then
    echo "4. Removing all project volumes..."
    docker volume ls --filter "name=seiji-watch" -q | xargs -r docker volume rm || true
else
    echo "4. Keeping volumes (--keep-volumes specified)"
fi

# Step 5: Prune system
echo "5. Pruning Docker system..."
docker system prune -f

# Step 6: Remove build cache
echo "6. Clearing Docker build cache..."
docker builder prune -f

# Step 7: Clean local directories
echo "7. Cleaning local directories..."

# Remove Python cache
find "$PROJECT_ROOT/services" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/services" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/services" -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove Node.js build artifacts (but keep node_modules for faster rebuilds)
rm -rf "$PROJECT_ROOT/services/web-frontend/.next" 2>/dev/null || true
rm -rf "$PROJECT_ROOT/services/web-frontend/out" 2>/dev/null || true

# Remove test results
rm -rf "$PROJECT_ROOT/test-results" 2>/dev/null || true
rm -rf "$PROJECT_ROOT/coverage" 2>/dev/null || true

echo ""
echo "====================================================="
echo -e "${GREEN}✓ Reset complete!${NC}"
echo "====================================================="
echo ""

# Show next steps
echo "Next steps:"
echo "  1. Review and update .env file if needed"
echo "  2. Start services: ./scripts/docker/start.sh [profile]"
echo ""

if [ "$KEEP_VOLUMES" = true ]; then
    echo -e "${BLUE}ℹ${NC} Data volumes were preserved. Your data is still available."
else
    echo -e "${YELLOW}⚠${NC} All data has been deleted. You'll start with a clean database."
fi

echo ""

# Offer to start services
read -p "Would you like to start core services now? (y/n): " start_now
if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
    echo ""
    exec "$SCRIPT_DIR/start.sh" core
fi