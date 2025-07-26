#!/bin/bash
# Setup script for Workload Identity Federation
# This script helps configure WIF for GitHub Actions

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REPO_OWNER="bxtxh"
REPO_NAME="seiji-watch"

echo -e "${GREEN}Diet Issue Tracker - Workload Identity Federation Setup${NC}"
echo "========================================================="

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}Error: gcloud CLI is not installed${NC}"
        echo "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}Error: terraform is not installed${NC}"
        echo "Please install Terraform: https://www.terraform.io/downloads"
        exit 1
    fi
    
    # Check if logged in to gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        echo -e "${RED}Error: Not logged in to gcloud${NC}"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: GCP_PROJECT_ID environment variable not set${NC}"
        echo "Please run: export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All prerequisites met${NC}"
}

# Enable required APIs
enable_apis() {
    echo -e "\n${YELLOW}Enabling required APIs...${NC}"
    
    APIS=(
        "iam.googleapis.com"
        "iamcredentials.googleapis.com"
        "sts.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        echo -n "Enabling $api... "
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}already enabled${NC}"
        fi
    done
}

# Apply Terraform configuration
apply_terraform() {
    echo -e "\n${YELLOW}Applying Terraform configuration...${NC}"
    
    cd infra
    
    # Initialize Terraform
    echo "Initializing Terraform..."
    terraform init \
        -backend-config="bucket=${PROJECT_ID}-terraform-state" \
        -backend-config="prefix=terraform/state/workload-identity"
    
    # Plan changes
    echo -e "\n${YELLOW}Planning Terraform changes...${NC}"
    terraform plan \
        -target=google_iam_workload_identity_pool.github_actions \
        -target=google_iam_workload_identity_pool_provider.github_actions \
        -target=google_service_account.github_actions \
        -target=google_project_iam_member.github_actions_roles \
        -target=google_service_account_iam_member.github_actions_workload_identity \
        -out=wif.tfplan
    
    # Apply changes
    echo -e "\n${YELLOW}Applying changes...${NC}"
    terraform apply wif.tfplan
    
    # Get outputs
    WIF_PROVIDER=$(terraform output -raw workload_identity_provider)
    SERVICE_ACCOUNT=$(terraform output -raw service_account_email)
    
    cd ..
    
    echo -e "\n${GREEN}✓ Terraform configuration applied${NC}"
}

# Display GitHub configuration
display_github_config() {
    echo -e "\n${GREEN}GitHub Repository Configuration${NC}"
    echo "================================="
    echo
    echo "Add these as repository variables (not secrets) in GitHub:"
    echo "Settings → Secrets and variables → Actions → Variables"
    echo
    echo -e "${YELLOW}WIF_PROVIDER:${NC}"
    echo "$WIF_PROVIDER"
    echo
    echo -e "${YELLOW}WIF_SERVICE_ACCOUNT:${NC}"
    echo "$SERVICE_ACCOUNT"
    echo
    echo "After adding these variables, your GitHub Actions will use"
    echo "Workload Identity Federation for authentication."
}

# Verify WIF setup
verify_setup() {
    echo -e "\n${YELLOW}Verifying WIF setup...${NC}"
    
    # Check if pool exists
    if gcloud iam workload-identity-pools describe github-actions-pool \
        --location=global \
        --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${GREEN}✓ Workload Identity Pool exists${NC}"
    else
        echo -e "${RED}✗ Workload Identity Pool not found${NC}"
        return 1
    fi
    
    # Check if provider exists
    if gcloud iam workload-identity-pools providers describe github-actions-provider \
        --workload-identity-pool=github-actions-pool \
        --location=global \
        --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${GREEN}✓ OIDC Provider configured${NC}"
    else
        echo -e "${RED}✗ OIDC Provider not found${NC}"
        return 1
    fi
    
    # Check service account
    if gcloud iam service-accounts describe "github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --project="$PROJECT_ID" &>/dev/null; then
        echo -e "${GREEN}✓ Service account exists${NC}"
    else
        echo -e "${RED}✗ Service account not found${NC}"
        return 1
    fi
    
    echo -e "\n${GREEN}✓ WIF setup verified successfully${NC}"
}

# Main execution
main() {
    check_prerequisites
    enable_apis
    apply_terraform
    display_github_config
    verify_setup
    
    echo -e "\n${GREEN}Setup complete!${NC}"
    echo
    echo "Next steps:"
    echo "1. Add the variables to your GitHub repository"
    echo "2. Push changes to trigger a workflow run"
    echo "3. Monitor the Actions tab for successful authentication"
    echo "4. Remove GCP_SERVICE_ACCOUNT_JSON secret from GitHub"
}

# Run main function
main