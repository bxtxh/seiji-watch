#!/bin/bash

# Airtable to Supabase Migration Deployment Script
# Usage: ./deploy_migration.sh [environment] [phase]
# Example: ./deploy_migration.sh staging 1

set -e

# Configuration
ENVIRONMENT=${1:-staging}
PHASE=${2:-1}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="${PROJECT_ROOT}/logs/deployment"
BACKUP_DIR="${PROJECT_ROOT}/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "${LOG_DIR}"
mkdir -p "${BACKUP_DIR}"

# Logging
LOG_FILE="${LOG_DIR}/migration_deploy_${ENVIRONMENT}_${TIMESTAMP}.log"
exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Airtable to Supabase Migration Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "Phase: ${PHASE}"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Python version
    if ! python3 --version | grep -q "3.11"; then
        echo -e "${RED}Error: Python 3.11+ required${NC}"
        exit 1
    fi
    
    # Check required commands
    commands=("docker" "docker-compose" "psql" "redis-cli" "curl")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo -e "${RED}Error: $cmd is not installed${NC}"
            exit 1
        fi
    done
    
    # Check environment file
    ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
    if [ ! -f "${ENV_FILE}" ]; then
        echo -e "${RED}Error: Environment file ${ENV_FILE} not found${NC}"
        exit 1
    fi
    
    # Load environment variables
    export $(cat "${ENV_FILE}" | grep -v '^#' | xargs)
    
    echo -e "${GREEN}✓ Prerequisites checked${NC}"
}

# Function to validate connections
validate_connections() {
    echo -e "${YELLOW}Validating connections...${NC}"
    
    # Test Airtable connection
    echo "Testing Airtable connection..."
    if ! curl -s -H "Authorization: Bearer ${AIRTABLE_PAT}" \
        "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/Bills%20(%E6%B3%95%E6%A1%88)?maxRecords=1" \
        > /dev/null; then
        echo -e "${RED}Error: Cannot connect to Airtable${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Airtable connection OK${NC}"
    
    # Test Supabase connection
    echo "Testing Supabase connection..."
    if ! psql "${SUPABASE_DB_URL}" -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${RED}Error: Cannot connect to Supabase${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Supabase connection OK${NC}"
    
    # Test Redis connection
    echo "Testing Redis connection..."
    if ! redis-cli -h "${REDIS_HOST:-localhost}" ping > /dev/null; then
        echo -e "${RED}Error: Cannot connect to Redis${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Redis connection OK${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"
    
    cd "${PROJECT_ROOT}/infra/supabase"
    
    # Run SQL migrations
    for migration in migrations/*.sql; do
        echo "Applying $(basename "$migration")..."
        psql "${SUPABASE_DB_URL}" -f "$migration"
    done
    
    echo -e "${GREEN}✓ Database migrations completed${NC}"
}

# Function to create rollback point
create_rollback_point() {
    echo -e "${YELLOW}Creating rollback point...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    # Create rollback using CLI
    python3 scripts/migration_cli.py rollback create \
        --phase "${PHASE}" \
        --description "Pre-deployment backup ${ENVIRONMENT} ${TIMESTAMP}" \
        --type full
    
    # Export database schema
    pg_dump "${SUPABASE_DB_URL}" --schema-only > "${BACKUP_DIR}/schema_${TIMESTAMP}.sql"
    
    # Backup configuration
    cp -r "${PROJECT_ROOT}/infra" "${BACKUP_DIR}/infra_${TIMESTAMP}"
    
    echo -e "${GREEN}✓ Rollback point created${NC}"
}

# Function to deploy services
deploy_services() {
    echo -e "${YELLOW}Deploying services...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    # Build Docker images
    echo "Building Docker images..."
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" build
    
    # Stop existing services
    echo "Stopping existing services..."
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" down
    
    # Start services
    echo "Starting services..."
    docker-compose -f docker-compose.yml -f "docker-compose.${ENVIRONMENT}.yml" up -d \
        redis \
        migration-worker \
        sync-worker \
        monitoring
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    services=("migration-worker" "sync-worker" "monitoring")
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "${service}.*Up"; then
            echo -e "${GREEN}✓ ${service} is running${NC}"
        else
            echo -e "${RED}✗ ${service} failed to start${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}✓ Services deployed${NC}"
}

# Function to run initial migration
run_initial_migration() {
    echo -e "${YELLOW}Running initial data migration...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    # Validate before migration
    echo "Validating data consistency before migration..."
    python3 scripts/migration_cli.py migrate validate
    
    # Run full migration
    echo "Running full migration..."
    python3 scripts/migration_cli.py migrate full --batch-size 100
    
    # Validate after migration
    echo "Validating data consistency after migration..."
    python3 scripts/migration_cli.py migrate validate
    
    echo -e "${GREEN}✓ Initial migration completed${NC}"
}

# Function to start sync service
start_sync_service() {
    echo -e "${YELLOW}Starting synchronization service...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    # Start incremental sync
    python3 scripts/migration_cli.py sync start \
        --mode incremental \
        --interval 5 &
    
    SYNC_PID=$!
    echo "Sync service started with PID: ${SYNC_PID}"
    echo "${SYNC_PID}" > "${PROJECT_ROOT}/.sync.pid"
    
    # Verify sync is running
    sleep 5
    if kill -0 "${SYNC_PID}" 2>/dev/null; then
        echo -e "${GREEN}✓ Sync service is running${NC}"
    else
        echo -e "${RED}✗ Sync service failed to start${NC}"
        exit 1
    fi
}

# Function to configure monitoring
setup_monitoring() {
    echo -e "${YELLOW}Setting up monitoring...${NC}"
    
    # Create monitoring dashboard
    curl -X POST "http://localhost:8080/api/v2/monitoring/setup" \
        -H "Content-Type: application/json" \
        -d '{
            "environment": "'"${ENVIRONMENT}"'",
            "phase": '"${PHASE}"',
            "alerts_enabled": true,
            "metrics_retention_days": 30
        }'
    
    # Set up alert thresholds
    curl -X POST "http://localhost:8080/api/v2/monitoring/alerts/configure" \
        -H "Content-Type: application/json" \
        -d '{
            "sync_lag_threshold_minutes": 30,
            "error_rate_threshold": 0.05,
            "consistency_threshold": 0.95
        }'
    
    echo -e "${GREEN}✓ Monitoring configured${NC}"
}

# Function to run health checks
run_health_checks() {
    echo -e "${YELLOW}Running health checks...${NC}"
    
    # Check API health
    if curl -s "http://localhost:8080/api/v2/monitoring/health" | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✓ API health check passed${NC}"
    else
        echo -e "${RED}✗ API health check failed${NC}"
        exit 1
    fi
    
    # Check data consistency
    python3 scripts/migration_cli.py migrate validate
    
    # Check sync status
    python3 scripts/migration_cli.py sync status
    
    echo -e "${GREEN}✓ All health checks passed${NC}"
}

# Function to generate deployment report
generate_report() {
    echo -e "${YELLOW}Generating deployment report...${NC}"
    
    REPORT_FILE="${LOG_DIR}/deployment_report_${TIMESTAMP}.md"
    
    cat > "${REPORT_FILE}" << EOF
# Deployment Report

## Deployment Information
- **Environment**: ${ENVIRONMENT}
- **Phase**: ${PHASE}
- **Timestamp**: ${TIMESTAMP}
- **Deployed By**: $(whoami)
- **Host**: $(hostname)

## Migration Statistics
\`\`\`
$(python3 scripts/migration_cli.py migrate validate)
\`\`\`

## Service Status
\`\`\`
$(docker-compose ps)
\`\`\`

## Sync Status
\`\`\`
$(python3 scripts/migration_cli.py sync status)
\`\`\`

## Health Check Results
\`\`\`
$(curl -s "http://localhost:8080/api/v2/monitoring/health" | python3 -m json.tool)
\`\`\`

## Rollback Points
\`\`\`
$(python3 scripts/migration_cli.py rollback list --phase "${PHASE}")
\`\`\`

## Log Files
- Main deployment log: ${LOG_FILE}
- Docker logs: \`docker-compose logs\`
- Migration logs: ${PROJECT_ROOT}/logs/migration.log
- Sync logs: ${PROJECT_ROOT}/logs/sync.log

EOF
    
    echo -e "${GREEN}✓ Deployment report generated: ${REPORT_FILE}${NC}"
}

# Main deployment flow
main() {
    echo "Starting deployment at $(date)"
    
    # Phase 1: Preparation
    check_prerequisites
    validate_connections
    
    # Phase 2: Backup
    create_rollback_point
    
    # Phase 3: Database setup
    run_migrations
    
    # Phase 4: Service deployment
    deploy_services
    
    # Phase 5: Data migration (only for initial deployment)
    if [ "${PHASE}" == "1" ]; then
        run_initial_migration
    fi
    
    # Phase 6: Synchronization
    start_sync_service
    
    # Phase 7: Monitoring
    setup_monitoring
    
    # Phase 8: Validation
    run_health_checks
    
    # Phase 9: Reporting
    generate_report
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo "Environment: ${ENVIRONMENT}"
    echo "Phase: ${PHASE}"
    echo "Time: $(date)"
    echo "Report: ${LOG_DIR}/deployment_report_${TIMESTAMP}.md"
}

# Trap errors and cleanup
trap 'echo -e "${RED}Deployment failed! Check logs: ${LOG_FILE}${NC}"; exit 1' ERR

# Run main deployment
main