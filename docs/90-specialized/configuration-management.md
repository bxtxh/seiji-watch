# Configuration Management Guide

Last Updated: 2025-01-27

## Overview

This guide documents all configuration files in the Diet Issue Tracker project and provides best practices for managing configurations across different environments.

## Environment Configuration Files

### Root Environment Files

| File               | Purpose                               | Usage                                  |
| ------------------ | ------------------------------------- | -------------------------------------- |
| `.env.template`    | Template with all available variables | Copy and customize for new deployments |
| `.env.development` | Development environment settings      | Local development (copy to `.env`)     |
| `.env.staging`     | Staging environment settings          | Staging deployments                    |
| `.env.production`  | Production environment settings       | Production deployments                 |

### Key Principles

1. **Never commit secrets** - Use `.env` files locally, Secret Manager in cloud
2. **Environment separation** - Each environment has its own configuration
3. **Secure defaults** - Production configs are restrictive by default
4. **Documentation** - Every variable must be documented

## Service Configuration

### Python Services (Poetry-based)

All Python services use Poetry for dependency management:

- `services/api_gateway/pyproject.toml`
- `services/ingest-worker/pyproject.toml`
- `shared/pyproject.toml`

**Note**: `requirements.txt` files have been removed in favor of Poetry standardization.

### Frontend Service (Next.js)

| File                   | Purpose                    |
| ---------------------- | -------------------------- |
| `package.json`         | Dependencies and scripts   |
| `tsconfig.json`        | TypeScript configuration   |
| `next.config.js`       | Next.js framework settings |
| `tailwind.config.js`   | Tailwind CSS customization |
| `jest.config.js`       | Unit testing configuration |
| `playwright.config.ts` | E2E testing configuration  |

### Docker Configuration

Each service has a `Dockerfile` for containerization:

- `services/api_gateway/Dockerfile`
- `services/ingest-worker/Dockerfile`
- `services/web-frontend/Dockerfile`

**Note**: `Dockerfile.simple` has been removed as it referenced obsolete code.

## Infrastructure Configuration

### Terraform Files

Located in `/infra/`:

| File                              | Purpose                            |
| --------------------------------- | ---------------------------------- |
| `terraform.tfvars.example`        | Variable template                  |
| `staging-external-testing.tfvars` | Staging environment variables      |
| `*.tf` files                      | Infrastructure as code definitions |

### Environment-Specific Values

- **Development**: Local resources, minimal cost
- **Staging**: Cloud resources, similar to production
- **Production**: Full scale, high availability

## CI/CD Configuration

### GitHub Actions Workflows

Located in `.github/workflows/`:

| Workflow                       | Purpose                  | Trigger                    |
| ------------------------------ | ------------------------ | -------------------------- |
| `ci-cd.yml`                    | Main deployment pipeline | Push to main/feat branches |
| `pr-check.yml`                 | Pull request validation  | PR creation/update         |
| `infrastructure.yml`           | Terraform deployment     | Manual/scheduled           |
| `staging-external-testing.yml` | External user testing    | Manual trigger             |

## Secret Management

### Local Development

1. Copy `.env.development` to `.env`
2. Add your personal API keys
3. Never commit `.env` file

### Cloud Environments

Secrets are managed via GCP Secret Manager:

```bash
# List secrets
gcloud secrets list --project=$PROJECT_ID

# Create a secret
gcloud secrets create SECRET_NAME --data-file=-

# Update a secret
gcloud secrets versions add SECRET_NAME --data-file=-
```

## Configuration Validation

### Pre-deployment Checklist

1. **Environment Variables**
   - [ ] All required variables are set
   - [ ] No hardcoded secrets in code
   - [ ] Environment-specific values are correct

2. **Dependencies**
   - [ ] Python dependencies locked in `poetry.lock`
   - [ ] Node dependencies locked in `package-lock.json`
   - [ ] Docker base images are up to date

3. **Infrastructure**
   - [ ] Terraform plan shows expected changes
   - [ ] Resource limits are appropriate
   - [ ] Backup strategies are in place

### Validation Script

```bash
# Run configuration validation
./scripts/validate-config.sh [environment]
```

## Adding New Configuration

### For New Services

1. Create `pyproject.toml` (Python) or `package.json` (Node.js)
2. Add service-specific environment variables to `.env.template`
3. Create `Dockerfile` following existing patterns
4. Update `docker-compose.yml` for local development
5. Add CI/CD configuration to workflows

### For New Environment Variables

1. Add to `.env.template` with description
2. Add to all environment-specific files with appropriate values
3. Document in service README
4. Update deployment configurations

## Common Issues and Solutions

### Issue: Missing Environment Variable

**Symptom**: Application fails to start with "missing required environment variable"

**Solution**:

1. Check `.env` file exists and contains the variable
2. Verify variable name matches exactly (case-sensitive)
3. For cloud deployments, check Secret Manager

### Issue: Dependency Conflicts

**Symptom**: Build fails with dependency resolution errors

**Solution**:

1. For Python: `poetry lock --no-update`
2. For Node.js: `rm -rf node_modules package-lock.json && npm install`
3. Check for version conflicts in `pyproject.toml` or `package.json`

### Issue: Docker Build Failures

**Symptom**: Docker image fails to build

**Solution**:

1. Check base image is available
2. Verify all COPY paths are correct
3. Ensure build context includes necessary files
4. Check for platform-specific issues (ARM vs x86)

## Best Practices

1. **Version Control**
   - Commit configuration changes separately from code changes
   - Use meaningful commit messages for config updates
   - Tag releases with configuration versions

2. **Security**
   - Rotate secrets regularly
   - Use least privilege principle
   - Audit access to production configs

3. **Documentation**
   - Keep this guide updated
   - Document non-obvious configuration choices
   - Include examples for complex configurations

4. **Testing**
   - Test configuration changes in staging first
   - Have rollback plans for config updates
   - Monitor application after config changes

## Migration Notes

### Recent Changes (2025-01-27)

1. **Removed `requirements.txt`** - All Python services now use Poetry exclusively
2. **Removed `Dockerfile.simple`** - Obsolete file referencing deleted code
3. **Added environment-specific `.env` files** - Better separation of concerns
4. **Standardized configuration structure** - Consistent patterns across services

<!--
### Historical Note (Commented for Reference)
Previously, the project used a mix of requirements.txt and pyproject.toml for Python dependencies.
This caused confusion and potential version conflicts. As of 2025-01-27, we've standardized on
Poetry (pyproject.toml) for all Python services. The old requirements.txt approach was:
- Less precise about dependency versions
- Didn't handle dev dependencies well
- Required manual pip freeze updates
-->

## Contact

For configuration-related questions:

- Check service-specific README files
- Review deployment documentation
- Contact the DevOps team for infrastructure configs
