# Workload Identity Federation Setup Guide

This guide documents the setup and configuration of Workload Identity Federation (WIF) for the Diet Issue Tracker project, replacing service account JSON keys with keyless authentication.

## Overview

Workload Identity Federation enables GitHub Actions to authenticate with Google Cloud Platform without storing long-lived credentials. This significantly improves security by:

- Eliminating the risk of exposed service account keys
- Providing short-lived, automatically rotated credentials
- Enabling fine-grained access control based on repository and branch

## Architecture

```
GitHub Actions (OIDC Token) → Workload Identity Pool → Service Account → GCP Resources
```

## Setup Instructions

### 1. Deploy Terraform Configuration

First, apply the Workload Identity Federation configuration:

```bash
cd infra
terraform apply -target=module.workload_identity
```

This will create:
- Workload Identity Pool: `github-actions-pool`
- OIDC Provider: `github-actions-provider`
- Service Account: `github-actions-sa@<project-id>.iam.gserviceaccount.com`

### 2. Configure GitHub Repository

After Terraform completes, note the outputs:

```bash
terraform output workload_identity_provider
terraform output service_account_email
```

Add these as GitHub repository variables (not secrets):
- `WIF_PROVIDER`: The workload identity provider path
- `WIF_SERVICE_ACCOUNT`: The service account email

Navigate to: Settings → Secrets and variables → Actions → Variables

### 3. Remove Service Account JSON Key

Once WIF is working, remove the old service account key:

1. Delete the `GCP_SERVICE_ACCOUNT_JSON` secret from GitHub
2. Revoke the old service account key in GCP Console

## Usage in GitHub Actions

The updated workflow uses WIF authentication:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ vars.WIF_PROVIDER }}
    service_account: ${{ vars.WIF_SERVICE_ACCOUNT }}
```

## Security Controls

### Repository Restrictions

The WIF provider is configured to only accept tokens from:
- Repository owner: `bxtxh`
- Repository: `seiji-watch`

This is enforced via the attribute condition in Terraform:

```hcl
attribute_condition = "assertion.repository_owner == 'bxtxh'"
```

### Service Account Permissions

The service account has the following roles:
- `roles/run.admin`: Deploy Cloud Run services
- `roles/storage.admin`: Manage storage buckets
- `roles/cloudsql.client`: Connect to Cloud SQL
- `roles/secretmanager.secretAccessor`: Read secrets
- `roles/iam.serviceAccountUser`: Act as service account

### Token Lifetime

OIDC tokens from GitHub Actions are valid for:
- 10 minutes for the initial token
- 1 hour for the access token after exchange

## Troubleshooting

### Authentication Failures

If authentication fails, check:

1. **Provider Configuration**: Ensure the WIF provider URL is correct
2. **Service Account**: Verify the service account email matches
3. **IAM Bindings**: Check that workloadIdentityUser binding exists
4. **Token Claims**: Verify the repository matches the attribute condition

### Debug Authentication Issues

Enable debug logging in the workflow:

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ vars.WIF_PROVIDER }}
    service_account: ${{ vars.WIF_SERVICE_ACCOUNT }}
  env:
    ACTIONS_STEP_DEBUG: true
```

### Common Errors

1. **"Unable to acquire impersonation credentials"**
   - Check the workloadIdentityUser IAM binding
   - Verify the principalSet matches your repository

2. **"Permission 'iam.serviceAccounts.getAccessToken' denied"**
   - The WIF configuration may be incomplete
   - Run `terraform apply` again to ensure all resources are created

## Maintenance

### Rotating Credentials

WIF handles credential rotation automatically. No manual intervention needed.

### Adding New Repositories

To allow additional repositories:

1. Update the attribute condition in `workload_identity.tf`
2. Add new principalSet bindings for each repository
3. Apply Terraform changes

### Monitoring

Monitor WIF usage via:
- Cloud Logging: Filter by `protoPayload.serviceName="sts.googleapis.com"`
- Cloud Monitoring: Track STS token exchange metrics

## Security Benefits

1. **No Long-Lived Credentials**: Eliminates service account key exposure risk
2. **Automatic Rotation**: Tokens expire and rotate automatically
3. **Audit Trail**: All authentications are logged with repository context
4. **Least Privilege**: Access is scoped to specific repositories and branches
5. **Compliance**: Meets security best practices for CI/CD authentication