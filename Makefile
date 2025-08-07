# ===================================================
# Diet Issue Tracker - Makefile
# ===================================================
# Convenient commands for Docker-based development

.PHONY: help
help: ## Show this help message
	@echo "Diet Issue Tracker - Docker Development Commands"
	@echo "================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make dev-setup    # Initial development setup"
	@echo "  make up           # Start all services"
	@echo "  make test         # Run all tests"
	@echo "  make build-prod   # Build production images"

# ===================================================
# Variables
# ===================================================
DOCKER_COMPOSE = docker compose
COMPOSE_FILES = -f docker-compose.yml
COMPOSE_TEST_FILES = -f docker-compose.yml -f docker-compose.test.yml
COMPOSE_PROD_FILES = -f docker-compose.yml -f docker-compose.prod.yml

# Git metadata for production builds
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
VERSION := $(shell git describe --tags --always 2>/dev/null || echo "dev")
BUILD_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')

# Service list
PYTHON_SERVICES = api-gateway data-processor diet-scraper stt-worker vector-store notifications-worker
NODE_SERVICES = web-frontend
ALL_SERVICES = $(PYTHON_SERVICES) $(NODE_SERVICES)

# ===================================================
# Development Setup
# ===================================================
.PHONY: dev-setup
dev-setup: ## Initial development environment setup
	@echo "Setting up development environment..."
	@cp -n .env.example .env || true
	@echo "✓ Environment file created"
	@$(MAKE) build
	@echo "✓ Docker images built"
	@echo ""
	@echo "Development setup complete! Run 'make up' to start services."

.PHONY: install
install: ## Install dependencies locally (for IDE support)
	@echo "Installing local dependencies..."
	@for service in $(PYTHON_SERVICES); do \
		echo "Installing $$service dependencies..."; \
		cd services/$$service && poetry install || true; \
		cd ../..; \
	done
	@cd services/web-frontend && npm install
	@echo "✓ Dependencies installed"

# ===================================================
# Docker Build Commands
# ===================================================
.PHONY: build
build: ## Build all Docker images for development
	@echo "Building Docker images..."
	@COMPOSE_PROFILES=full $(DOCKER_COMPOSE) build --parallel

.PHONY: build-service
build-service: ## Build specific service (use SERVICE=api-gateway)
	@echo "Building $(SERVICE)..."
	@$(DOCKER_COMPOSE) build $(SERVICE)

.PHONY: build-prod
build-prod: ## Build production images with metadata
	@echo "Building production images..."
	@for service in $(ALL_SERVICES); do \
		echo "Building $$service (production)..."; \
		docker build \
			--target production \
			--build-arg GIT_COMMIT=$(GIT_COMMIT) \
			--build-arg VERSION=$(VERSION) \
			--build-arg BUILD_DATE=$(BUILD_DATE) \
			-t $$service:$(VERSION) \
			-t $$service:latest \
			./services/$$service; \
	done
	@echo "✓ Production images built"

.PHONY: rebuild
rebuild: ## Rebuild all images without cache
	@echo "Rebuilding all images..."
	@COMPOSE_PROFILES=full $(DOCKER_COMPOSE) build --no-cache --parallel

# ===================================================
# Docker Run Commands
# ===================================================
.PHONY: up
up: ## Start all core services
	@echo "Starting core services..."
	@./scripts/docker/start.sh core

.PHONY: up-all
up-all: ## Start ALL services
	@echo "Starting all services..."
	@./scripts/docker/start.sh full

.PHONY: up-workers
up-workers: ## Start worker services
	@echo "Starting worker services..."
	@./scripts/docker/start.sh workers

.PHONY: down
down: ## Stop all services
	@echo "Stopping services..."
	@$(DOCKER_COMPOSE) --profile full down

.PHONY: restart
restart: down up ## Restart all services

.PHONY: reset
reset: ## Reset environment (WARNING: destroys data)
	@./scripts/docker/reset.sh

# ===================================================
# Testing Commands
# ===================================================
.PHONY: test
test: ## Run all tests in Docker
	@echo "Running all tests..."
	@$(DOCKER_COMPOSE) $(COMPOSE_TEST_FILES) up --abort-on-container-exit --exit-code-from test-runner

.PHONY: test-service
test-service: ## Test specific service (use SERVICE=api-gateway)
	@echo "Testing $(SERVICE)..."
	@docker build --target test -t $(SERVICE)-test ./services/$(SERVICE)
	@docker run --rm $(SERVICE)-test

.PHONY: test-python
test-python: ## Run Python tests only
	@echo "Running Python tests..."
	@for service in $(PYTHON_SERVICES); do \
		echo "Testing $$service..."; \
		$(MAKE) test-service SERVICE=$$service || true; \
	done

.PHONY: test-frontend
test-frontend: ## Run frontend tests only
	@echo "Running frontend tests..."
	@$(MAKE) test-service SERVICE=web-frontend

.PHONY: test-e2e
test-e2e: ## Run E2E tests
	@echo "Running E2E tests..."
	@COMPOSE_PROFILES=core $(DOCKER_COMPOSE) up -d
	@sleep 10
	@$(DOCKER_COMPOSE) run --rm web-frontend npm run test:e2e
	@$(MAKE) down

.PHONY: lint
lint: ## Run linting checks
	@echo "Running linting..."
	@for service in $(PYTHON_SERVICES); do \
		echo "Linting $$service..."; \
		docker run --rm -v $(PWD)/services/$$service:/app \
			python:3.11-slim bash -c "pip install ruff black && cd /app && ruff check . && black --check ."; \
	done
	@docker run --rm -v $(PWD)/services/web-frontend:/app \
		node:18-alpine sh -c "cd /app && npm run lint"

.PHONY: format
format: ## Auto-format code
	@echo "Formatting code..."
	@for service in $(PYTHON_SERVICES); do \
		echo "Formatting $$service..."; \
		docker run --rm -v $(PWD)/services/$$service:/app \
			python:3.11-slim bash -c "pip install ruff black && cd /app && ruff check --fix . && black ."; \
	done
	@docker run --rm -v $(PWD)/services/web-frontend:/app \
		node:18-alpine sh -c "cd /app && npm run format"

# ===================================================
# Utility Commands
# ===================================================
.PHONY: logs
logs: ## View logs (use SERVICE=api-gateway for specific service)
	@./scripts/docker/logs.sh $(SERVICE)

.PHONY: shell
shell: ## Access service shell (use SERVICE=api-gateway)
	@./scripts/docker/shell.sh $(SERVICE)

.PHONY: ps
ps: ## Show running containers
	@$(DOCKER_COMPOSE) ps

.PHONY: health
health: ## Check service health
	@echo "Checking service health..."
	@$(DOCKER_COMPOSE) ps --format "table {{.Service}}\t{{.Status}}"

.PHONY: clean
clean: ## Clean up containers, images, and volumes
	@echo "Cleaning up Docker resources..."
	@$(DOCKER_COMPOSE) --profile full down -v
	@docker system prune -f
	@echo "✓ Cleanup complete"

.PHONY: validate-env
validate-env: ## Validate environment variables
	@./scripts/docker/validate-env.sh

# ===================================================
# Security Commands
# ===================================================
.PHONY: security-scan
security-scan: ## Run security scans on images
	@echo "Running security scans..."
	@for service in $(ALL_SERVICES); do \
		echo "Scanning $$service..."; \
		docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
			aquasec/trivy image $$service:latest || true; \
	done

.PHONY: secrets-check
secrets-check: ## Check for exposed secrets
	@echo "Checking for exposed secrets..."
	@docker run --rm -v $(PWD):/src \
		trufflesecurity/trufflehog:latest filesystem /src \
		--exclude-paths=/src/.trufflehog-exclude

# ===================================================
# CI/CD Commands
# ===================================================
.PHONY: ci-test
ci-test: ## Run CI tests (used by GitHub Actions)
	@echo "Running CI tests..."
	@$(DOCKER_COMPOSE) $(COMPOSE_TEST_FILES) build test-runner
	@$(DOCKER_COMPOSE) $(COMPOSE_TEST_FILES) up --abort-on-container-exit --exit-code-from test-runner

.PHONY: ci-build
ci-build: ## Build images for CI
	@echo "Building CI images..."
	@for service in $(ALL_SERVICES); do \
		docker build --target test -t $$service:test ./services/$$service; \
		docker build --target production -t $$service:prod ./services/$$service; \
	done

# ===================================================
# Database Commands
# ===================================================
.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@$(DOCKER_COMPOSE) run --rm api-gateway python -m alembic upgrade head

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys data)
	@echo "Resetting database..."
	@$(DOCKER_COMPOSE) exec postgres psql -U seiji_watch_user -c "DROP DATABASE IF EXISTS seiji_watch;"
	@$(DOCKER_COMPOSE) exec postgres psql -U seiji_watch_user -c "CREATE DATABASE seiji_watch;"
	@$(MAKE) db-migrate

.PHONY: db-backup
db-backup: ## Backup database
	@echo "Backing up database..."
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec postgres pg_dump -U seiji_watch_user seiji_watch | gzip > backups/db-backup-$$(date +%Y%m%d-%H%M%S).sql.gz
	@echo "✓ Database backed up"

# ===================================================
# Monitoring Commands
# ===================================================
.PHONY: stats
stats: ## Show container statistics
	@docker stats --no-stream

.PHONY: monitor
monitor: ## Monitor services (live stats)
	@docker stats

# Default target
.DEFAULT_GOAL := help