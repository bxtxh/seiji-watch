#!/bin/bash

# ===================================================
# Local Security Check Script
# ===================================================
# Run security checks locally before pushing to CI/CD

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}Starting Security Checks${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        FAILED_CHECKS+=("$2")
    fi
}

FAILED_CHECKS=()

# ===================================================
# 1. Container Security with Trivy
# ===================================================
echo -e "\n${BLUE}1. Container Security Scan${NC}"
if command_exists trivy; then
    for service in api-gateway web-frontend data-processor; do
        echo "Scanning $service..."
        if [ -f "$PROJECT_ROOT/services/$service/Dockerfile" ]; then
            docker build -t $service:security-test "$PROJECT_ROOT/services/$service" 2>/dev/null
            trivy image --severity HIGH,CRITICAL --exit-code 1 $service:security-test >/dev/null 2>&1
            print_status $? "$service container scan"
        fi
    done
else
    echo -e "${YELLOW}⚠ Trivy not installed. Install with: brew install trivy${NC}"
fi

# ===================================================
# 2. Secret Detection
# ===================================================
echo -e "\n${BLUE}2. Secret Detection${NC}"

# Check for common secret patterns
echo "Checking for exposed secrets..."
SECRET_PATTERNS=(
    "AKIA[0-9A-Z]{16}"  # AWS Access Key
    "(?i)api[_-]?key"
    "(?i)secret[_-]?key"
    "(?i)password"
    "(?i)token"
    "-----BEGIN RSA PRIVATE KEY-----"
    "-----BEGIN OPENSSH PRIVATE KEY-----"
)

SECRETS_FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -r -E "$pattern" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude="*.md" "$PROJECT_ROOT" >/dev/null 2>&1; then
        SECRETS_FOUND=1
    fi
done

if [ $SECRETS_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No obvious secrets detected${NC}"
else
    echo -e "${YELLOW}⚠ Potential secrets detected (may be false positives)${NC}"
fi

# ===================================================
# 3. Dependency Vulnerability Check
# ===================================================
echo -e "\n${BLUE}3. Dependency Vulnerabilities${NC}"

# Python dependencies
echo "Checking Python dependencies..."
if command_exists safety; then
    for service in api-gateway data-processor diet-scraper stt-worker vector-store notifications-worker; do
        if [ -f "$PROJECT_ROOT/services/$service/pyproject.toml" ]; then
            cd "$PROJECT_ROOT/services/$service"
            poetry export -f requirements.txt --without-hashes 2>/dev/null | safety check --stdin --short-report >/dev/null 2>&1
            print_status $? "$service Python dependencies"
        fi
    done
else
    echo -e "${YELLOW}⚠ Safety not installed. Install with: pip install safety${NC}"
fi

# Node.js dependencies
echo "Checking Node.js dependencies..."
if [ -f "$PROJECT_ROOT/services/web-frontend/package.json" ]; then
    cd "$PROJECT_ROOT/services/web-frontend"
    npm audit --audit-level=high >/dev/null 2>&1
    print_status $? "web-frontend Node.js dependencies"
fi

# ===================================================
# 4. Docker Security Best Practices
# ===================================================
echo -e "\n${BLUE}4. Docker Security Best Practices${NC}"

# Check Dockerfiles for security issues
DOCKER_ISSUES=0
for dockerfile in $(find "$PROJECT_ROOT" -name "Dockerfile*"); do
    # Check for running as root
    if ! grep -q "USER" "$dockerfile"; then
        echo -e "${YELLOW}⚠ $dockerfile may be running as root${NC}"
        DOCKER_ISSUES=1
    fi
    
    # Check for latest tags
    if grep -q ":latest" "$dockerfile"; then
        echo -e "${YELLOW}⚠ $dockerfile uses :latest tag${NC}"
        DOCKER_ISSUES=1
    fi
    
    # Check for sudo usage
    if grep -q "sudo" "$dockerfile"; then
        echo -e "${YELLOW}⚠ $dockerfile uses sudo${NC}"
        DOCKER_ISSUES=1
    fi
done

if [ $DOCKER_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ Dockerfile security checks passed${NC}"
fi

# ===================================================
# 5. Environment Variables Check
# ===================================================
echo -e "\n${BLUE}5. Environment Variables${NC}"

# Check for .env files in git
if git ls-files | grep -E "\.env$" >/dev/null 2>&1; then
    echo -e "${RED}✗ .env file tracked in git!${NC}"
    FAILED_CHECKS+=(".env file in git")
else
    echo -e "${GREEN}✓ No .env files in git${NC}"
fi

# Check if .env.example exists
if [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo -e "${GREEN}✓ .env.example template exists${NC}"
else
    echo -e "${YELLOW}⚠ Missing .env.example template${NC}"
fi

# ===================================================
# 6. HTTPS/TLS Configuration
# ===================================================
echo -e "\n${BLUE}6. TLS Configuration${NC}"

# Check nginx configuration
if [ -f "$PROJECT_ROOT/nginx/nginx.conf" ]; then
    # Check for weak TLS versions
    if grep -q "TLSv1.0\|TLSv1.1" "$PROJECT_ROOT/nginx/nginx.conf"; then
        echo -e "${RED}✗ Weak TLS versions enabled${NC}"
        FAILED_CHECKS+=("Weak TLS versions")
    else
        echo -e "${GREEN}✓ Strong TLS configuration${NC}"
    fi
    
    # Check for security headers
    HEADERS=("X-Frame-Options" "X-Content-Type-Options" "X-XSS-Protection")
    for header in "${HEADERS[@]}"; do
        if grep -q "$header" "$PROJECT_ROOT/nginx/nginx.conf"; then
            echo -e "${GREEN}✓ $header header configured${NC}"
        else
            echo -e "${YELLOW}⚠ Missing $header header${NC}"
        fi
    done
fi

# ===================================================
# 7. License Compliance
# ===================================================
echo -e "\n${BLUE}7. License Compliance${NC}"

# Check for LICENSE file
if [ -f "$PROJECT_ROOT/LICENSE" ]; then
    echo -e "${GREEN}✓ LICENSE file exists${NC}"
else
    echo -e "${YELLOW}⚠ No LICENSE file found${NC}"
fi

# ===================================================
# Summary
# ===================================================
echo -e "\n${BLUE}=====================================================${NC}"
echo -e "${BLUE}Security Check Summary${NC}"
echo -e "${BLUE}=====================================================${NC}"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All security checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Failed checks:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "${RED}  - $check${NC}"
    done
    echo -e "\n${YELLOW}Please fix the issues before deploying to production${NC}"
    exit 1
fi