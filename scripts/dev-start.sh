#!/bin/bash

# Development Environment Start Script
# This script starts all services for local development

set -e

echo "🎯 Starting Diet Issue Tracker development environment..."

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "❌ .env.local not found. Please run ./scripts/setup-dev.sh first."
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service health
echo "🔍 Checking service health..."

# PostgreSQL health check
if docker exec seiji-watch-postgres pg_isready -U seiji_watch_user -d seiji_watch >/dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
    exit 1
fi

# Redis health check
if docker exec seiji-watch-redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready"
    exit 1
fi

echo "🚀 All services are ready!"
echo ""
echo "🌐 Service URLs:"
echo "  - Adminer (Database): http://localhost:8080"
echo "  - API Gateway: http://localhost:8000 (when started)"
echo "  - Frontend: http://localhost:3000 (when started)"
echo ""
echo "▶️  To start the application services:"
echo "  Terminal 1: poetry run uvicorn services.api-gateway.main:app --reload --host 0.0.0.0 --port 8000"
echo "  Terminal 2: npm run dev --workspace=services/web-frontend"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"