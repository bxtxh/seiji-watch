#!/bin/bash

# Terraform Deployment Script for Diet Issue Tracker
# This script handles Terraform deployment with proper initialization and validation

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
ACTION="plan"
AUTO_APPROVE=false

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment (dev, staging, prod) [default: dev]"
    echo "  -a, --action ACTION      Terraform action (plan, apply, destroy) [default: plan]"
    echo "  -y, --auto-approve       Auto approve for apply/destroy actions"
    echo "  -h, --help              Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev -a plan                   # Plan development environment"
    echo "  $0 -e dev -a apply -y               # Apply development environment with auto-approve"
    echo "  $0 -e prod -a apply                 # Apply production environment (will prompt for approval)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -y|--auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}❌ Error: Environment must be dev, staging, or prod${NC}"
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
    echo -e "${RED}❌ Error: Action must be plan, apply, or destroy${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Diet Issue Tracker Terraform Deployment${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Action: ${ACTION}${NC}"
echo ""

# Change to infrastructure directory
cd "$(dirname "$0")/../infra"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ terraform.tfvars not found${NC}"
    echo -e "${YELLOW}💡 Please copy terraform.tfvars.example to terraform.tfvars and update with your values${NC}"
    echo ""
    echo "cp terraform.tfvars.example terraform.tfvars"
    echo "# Edit terraform.tfvars with your GCP project details"
    exit 1
fi

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ No active gcloud authentication found${NC}"
    echo -e "${YELLOW}💡 Please authenticate with gcloud:${NC}"
    echo "gcloud auth login"
    echo "gcloud auth application-default login"
    exit 1
fi

# Get project ID from terraform.tfvars
PROJECT_ID=$(grep -E '^project_id\s*=' terraform.tfvars | cut -d'"' -f2)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Could not extract project_id from terraform.tfvars${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Project ID: ${PROJECT_ID}${NC}"

# Set gcloud project
gcloud config set project "$PROJECT_ID"

# Initialize Terraform
echo -e "${YELLOW}🔧 Initializing Terraform...${NC}"
terraform init

# Validate Terraform configuration
echo -e "${YELLOW}🔍 Validating Terraform configuration...${NC}"
terraform validate

# Format Terraform files
terraform fmt

# Create workspace for environment if it doesn't exist
echo -e "${YELLOW}🏗️  Setting up Terraform workspace for ${ENVIRONMENT}...${NC}"
if ! terraform workspace list | grep -q "^[* ] ${ENVIRONMENT}$"; then
    terraform workspace new "$ENVIRONMENT"
else
    terraform workspace select "$ENVIRONMENT"
fi

# Execute Terraform action
case $ACTION in
    plan)
        echo -e "${YELLOW}📋 Running Terraform plan for ${ENVIRONMENT}...${NC}"
        terraform plan -var="environment=${ENVIRONMENT}" -out="tfplan-${ENVIRONMENT}"
        ;;
    apply)
        echo -e "${YELLOW}🚀 Running Terraform apply for ${ENVIRONMENT}...${NC}"
        
        # For production, always require manual approval unless explicitly auto-approved
        if [ "$ENVIRONMENT" = "prod" ] && [ "$AUTO_APPROVE" = false ]; then
            echo -e "${RED}⚠️  Production deployment detected${NC}"
            echo -e "${YELLOW}This will make changes to production infrastructure.${NC}"
            read -p "Are you sure you want to continue? (type 'yes'): " confirmation
            if [ "$confirmation" != "yes" ]; then
                echo -e "${YELLOW}Deployment cancelled${NC}"
                exit 0
            fi
        fi
        
        if [ "$AUTO_APPROVE" = true ]; then
            terraform apply -var="environment=${ENVIRONMENT}" -auto-approve
        else
            terraform apply -var="environment=${ENVIRONMENT}"
        fi
        
        echo -e "${GREEN}✅ Terraform apply completed successfully${NC}"
        echo ""
        echo -e "${BLUE}📝 Important outputs:${NC}"
        terraform output
        ;;
    destroy)
        echo -e "${RED}⚠️  Running Terraform destroy for ${ENVIRONMENT}${NC}"
        echo -e "${RED}This will DESTROY all infrastructure in ${ENVIRONMENT}!${NC}"
        
        if [ "$AUTO_APPROVE" = false ]; then
            read -p "Are you sure you want to destroy ${ENVIRONMENT} infrastructure? (type 'destroy'): " confirmation
            if [ "$confirmation" != "destroy" ]; then
                echo -e "${YELLOW}Destroy cancelled${NC}"
                exit 0
            fi
        fi
        
        if [ "$AUTO_APPROVE" = true ]; then
            terraform destroy -var="environment=${ENVIRONMENT}" -auto-approve
        else
            terraform destroy -var="environment=${ENVIRONMENT}"
        fi
        
        echo -e "${GREEN}✅ Terraform destroy completed${NC}"
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Terraform ${ACTION} completed successfully for ${ENVIRONMENT} environment${NC}"

# Post-deployment instructions
if [ "$ACTION" = "apply" ]; then
    echo ""
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo "1. Update your .env.local with the output values above"
    echo "2. Update the OpenAI API key in Secret Manager:"
    echo "   gcloud secrets versions add seiji-watch-openai-api-key-${ENVIRONMENT} --data-file=- <<< 'your-actual-api-key'"
    echo "3. Build and deploy your application containers"
    echo "4. Configure your domain and SSL certificates (for production)"
fi