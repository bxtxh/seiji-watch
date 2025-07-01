#!/bin/bash

# Health Check Script
# Verifies that all development services are running correctly

set -e

echo "🏥 Running health checks for Diet Issue Tracker..."

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service_name=$1
    local check_command=$2
    
    if eval "$check_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not healthy${NC}"
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local service_name=$1
    local url=$2
    
    if curl -s "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is responding at $url${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not responding at $url${NC}"
        return 1
    fi
}

echo "🐳 Checking Docker services..."

# Check PostgreSQL
check_service "PostgreSQL" "docker exec seiji-watch-postgres pg_isready -U seiji_watch_user -d seiji_watch"

# Check pgvector extension
echo "🔍 Checking pgvector extension..."
if docker exec seiji-watch-postgres psql -U seiji_watch_user -d seiji_watch -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
    echo -e "${GREEN}✅ pgvector extension is installed${NC}"
else
    echo -e "${RED}❌ pgvector extension is not installed${NC}"
fi

# Check Redis
check_service "Redis" "docker exec seiji-watch-redis redis-cli ping"

# Check Adminer
check_http "Adminer" "http://localhost:8080"

echo ""
echo "📊 Container status:"
docker-compose ps

echo ""
echo "💾 Database info:"
echo "  - Host: localhost:5432"
echo "  - Database: seiji_watch"
echo "  - Username: seiji_watch_user"
echo "  - Password: seiji_watch_pass"

echo ""
echo "🔗 Service URLs:"
echo "  - Adminer: http://localhost:8080"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"

# Check if API is running (optional)
if check_http "API Gateway" "http://localhost:8000/health" 2>/dev/null; then
    echo "  - API Gateway: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
fi

# Check if Frontend is running (optional)
if check_http "Frontend" "http://localhost:3000" 2>/dev/null; then
    echo "  - Frontend: http://localhost:3000"
fi

echo ""
echo -e "${YELLOW}💡 If any services are not healthy, try:${NC}"
echo "  - docker-compose down && docker-compose up -d"
echo "  - docker-compose logs [service-name] for debugging"