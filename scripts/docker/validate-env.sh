#!/bin/bash

# ===================================================
# Environment Variables Validation Script
# ===================================================
# This script validates that all required environment
# variables are set before starting Docker services

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# Load .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${YELLOW}Warning: .env file not found at $PROJECT_ROOT/.env${NC}"
    echo "Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${GREEN}Created .env file. Please fill in your actual values.${NC}"
    exit 1
fi

# Required environment variables
REQUIRED_VARS=(
    "ENVIRONMENT"
    "DATABASE_URL"
    "REDIS_URL"
)

# Required for production
PRODUCTION_VARS=(
    "JWT_SECRET_KEY"
    "AIRTABLE_ACCESS_TOKEN"
    "AIRTABLE_BASE_ID"
)

# Optional but recommended
OPTIONAL_VARS=(
    "OPENAI_API_KEY"
    "WEAVIATE_URL"
    "SENDGRID_API_KEY"
)

# Function to check if variable is set
check_var() {
    local var_name=$1
    local var_value=${!var_name}
    
    if [ -z "$var_value" ]; then
        return 1
    else
        return 0
    fi
}

# Function to mask sensitive values
mask_value() {
    local value=$1
    local length=${#value}
    
    if [ $length -le 8 ]; then
        echo "****"
    else
        echo "${value:0:4}****${value: -4}"
    fi
}

echo "====================================================="
echo "Validating Environment Variables"
echo "====================================================="
echo ""

# Check required variables
echo "Checking required variables..."
missing_required=()
for var in "${REQUIRED_VARS[@]}"; do
    if check_var "$var"; then
        masked_value=$(mask_value "${!var}")
        echo -e "${GREEN}✓${NC} $var: $masked_value"
    else
        echo -e "${RED}✗${NC} $var: NOT SET"
        missing_required+=("$var")
    fi
done

echo ""

# Check production variables if in production
if [ "$ENVIRONMENT" == "production" ]; then
    echo "Checking production variables..."
    for var in "${PRODUCTION_VARS[@]}"; do
        if check_var "$var"; then
            masked_value=$(mask_value "${!var}")
            echo -e "${GREEN}✓${NC} $var: $masked_value"
        else
            echo -e "${RED}✗${NC} $var: NOT SET"
            missing_required+=("$var")
        fi
    done
    echo ""
fi

# Check optional variables
echo "Checking optional variables..."
missing_optional=()
for var in "${OPTIONAL_VARS[@]}"; do
    if check_var "$var"; then
        masked_value=$(mask_value "${!var}")
        echo -e "${GREEN}✓${NC} $var: $masked_value"
    else
        echo -e "${YELLOW}⚠${NC} $var: NOT SET (optional)"
        missing_optional+=("$var")
    fi
done

echo ""
echo "====================================================="

# Report results
if [ ${#missing_required[@]} -gt 0 ]; then
    echo -e "${RED}ERROR: Missing required environment variables:${NC}"
    for var in "${missing_required[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables in your .env file"
    exit 1
fi

if [ ${#missing_optional[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warning: Some optional variables are not set:${NC}"
    for var in "${missing_optional[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Some features may be disabled"
fi

echo -e "${GREEN}Environment validation successful!${NC}"
echo ""

# Additional checks
echo "Additional checks:"

# Check if Docker is running
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is running"
else
    echo -e "${RED}✗${NC} Docker is not running. Please start Docker."
    exit 1
fi

# Check if docker-compose is installed
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose is installed"
else
    echo -e "${RED}✗${NC} Docker Compose is not installed"
    exit 1
fi

# Check available disk space (require at least 5GB)
available_space=$(df -h . | awk 'NR==2 {print $4}' | sed 's/[^0-9]//g')
if [ ! -z "$available_space" ] && [ "$available_space" -ge 5 ]; then
    echo -e "${GREEN}✓${NC} Sufficient disk space (${available_space}GB available)"
else
    echo -e "${YELLOW}⚠${NC} Disk space check skipped or low space"
fi

echo ""
echo "====================================================="
echo -e "${GREEN}All checks passed! Ready to start services.${NC}"
echo "====================================================="