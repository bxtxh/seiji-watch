#!/bin/bash

# Development Environment Setup Script
# This script sets up the local development environment

set -e

echo "🚀 Setting up Diet Issue Tracker development environment..."

# Check prerequisites
echo "📋 Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Please install Docker."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Please install Docker Compose."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Please install Python 3.11+."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Please install Node.js 18+."; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "❌ Poetry is required but not installed. Please install Poetry."; exit 1; }

echo "✅ All prerequisites are installed."

# Create .env.local from template if it doesn't exist
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from template..."
    cp .env.development .env.local
    echo "⚠️  Please update .env.local with your actual API keys and configuration."
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
poetry install

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if PostgreSQL is ready
echo "🔍 Checking PostgreSQL connection..."
until docker exec seiji-watch-postgres pg_isready -U seiji_watch_user -d seiji_watch; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

# Check if Redis is ready
echo "🔍 Checking Redis connection..."
until docker exec seiji-watch-redis redis-cli ping; do
    echo "Waiting for Redis to be ready..."
    sleep 2
done

echo "✅ Development environment setup complete!"
echo ""
echo "📖 Next steps:"
echo "  1. Update .env.local with your actual API keys"
echo "  2. Run 'npm run dev' to start the frontend"
echo "  3. Run 'poetry run uvicorn api-gateway.main:app --reload' to start the API"
echo "  4. Visit http://localhost:8080 for Adminer (database management)"
echo "  5. Visit http://localhost:3000 for the frontend"
echo "  6. Visit http://localhost:8000/docs for the API documentation"
echo ""
echo "🛠️  Useful commands:"
echo "  - docker-compose logs: View all service logs"
echo "  - docker-compose down: Stop all services"
echo "  - poetry shell: Activate Python virtual environment"