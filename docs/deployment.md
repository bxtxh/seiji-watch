# Diet Issue Tracker - Deployment Guide

## Overview

This guide covers the deployment of the complete Diet Issue Tracker platform with all microservices to Google Cloud Platform (GCP).

## Architecture Overview

The platform consists of 7 microservices:
- **diet-scraper**: Data collection from Diet websites
- **stt-worker**: Speech-to-text processing with Whisper
- **data-processor**: Data normalization and LLM analysis
- **vector-store**: Embedding generation and semantic search
- **api-gateway**: RESTful API with authentication
- **web-frontend**: Next.js PWA frontend
- **notifications-worker**: Email notification service

## Infrastructure Components

### GCP Services
- **Cloud Run**: Serverless containers for all services
- **Cloud SQL**: PostgreSQL 15 with pgvector extension
- **Cloud Storage**: Raw data and processed files
- **Artifact Registry**: Docker container registry
- **Cloud Pub/Sub**: Async message queue
- **Secret Manager**: API keys and credentials
- **Cloud Scheduler**: Cron jobs for batch processing
- **VPC**: Private networking with Cloud SQL access

## Prerequisites

### Local Development
- Docker & Docker Compose
- Terraform >= 1.0
- gcloud CLI
- Python 3.11+
- Node.js 18+
- Poetry (Python package manager)

### GCP Requirements
- GCP Project with billing enabled
- Required APIs enabled:
  - Cloud Run API
  - Cloud SQL Admin API
  - Artifact Registry API
  - Cloud Pub/Sub API
  - Secret Manager API
  - Cloud Scheduler API

## Deployment Steps

### 1. Infrastructure Setup

```bash
# Configure Terraform variables
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Edit terraform.tfvars with your project details

# Initialize and apply Terraform
cd infra
terraform init
terraform plan
terraform apply
```

### 2. Database Setup

```bash
# Connect to Cloud SQL
gcloud sql connect seiji-watch-db-${ENV} --user=postgres

# Run database migrations
cd shared
poetry run alembic upgrade head
```

### 3. Configure Secrets

```bash
# Set required secrets in Secret Manager
gcloud secrets create openai-api-key-${ENV} --data-file=- <<< 'your-key'
gcloud secrets create airtable-pat-${ENV} --data-file=- <<< 'your-pat'
gcloud secrets create sendgrid-api-key-${ENV} --data-file=- <<< 'your-key'
gcloud secrets create jwt-secret-key-${ENV} --data-file=- <<< 'your-secret'
```

### 4. Build and Deploy Services

Using GitHub Actions (recommended):
```bash
# Push to main branch triggers automatic deployment
git push origin main
```

Manual deployment:
```bash
# Build and push Docker images
./scripts/build-and-push.sh -e ${ENV}

# Deploy services to Cloud Run
./scripts/deploy-services.sh -e ${ENV}
```

### 5. Configure Cloud Scheduler Jobs

```bash
# Daily data collection (2 AM JST)
gcloud scheduler jobs create http diet-scraper-daily \
  --location=asia-northeast1 \
  --schedule="0 17 * * *" \
  --uri="https://diet-scraper-${ENV}-xxx.run.app/trigger/daily" \
  --http-method=POST

# Notification batch (10 PM JST)
gcloud scheduler jobs create http notifications-daily \
  --location=asia-northeast1 \
  --schedule="0 13 * * *" \
  --uri="https://notifications-worker-${ENV}-xxx.run.app/send-daily" \
  --http-method=POST
```

## Environment Configuration

### Development Environment
- Uses local PostgreSQL via Docker Compose
- Services run on localhost with different ports
- Hot reload enabled for all services

### Staging Environment
- Mirrors production infrastructure
- Uses separate GCP project or namespace
- Automated deployment from main branch

### Production Environment
- Manual approval required for deployment
- Blue-green deployment strategy
- Health checks and rollback capability

## Service-Specific Configuration

### diet-scraper
- Rate limiting: 1-2 second delays
- Respects robots.txt
- NDL API rate limit: ≤3 req/s

### stt-worker
- Whisper large-v3 model
- Audio files stored in Cloud Storage
- WER validation ≤15%

### data-processor
- OpenAI GPT-4 for analysis
- Airtable integration for dynamic data
- Batch processing capabilities

### vector-store
- pgvector for embeddings
- Japanese-optimized models
- Incremental indexing

### api-gateway
- JWT authentication
- CORS configuration
- Rate limiting with Redis

### web-frontend
- CDN distribution
- PWA manifest configuration
- Environment-specific API URLs

### notifications-worker
- SendGrid configuration
- Daily batch at 22:00 JST
- Idempotency checks

## Monitoring and Maintenance

### Health Checks
All services expose health endpoints:
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check

### Logging
- Structured JSON logging
- Cloud Logging integration
- Log levels: DEBUG, INFO, WARNING, ERROR

### Metrics
- Request latency (p50, p95, p99)
- Error rates
- Processing queue depth
- Database connection pool

### Alerts
Configure alerts in Cloud Monitoring for:
- Service downtime
- High error rates
- Slow response times
- Failed batch jobs

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check VPC connector configuration
   - Verify Cloud SQL proxy is running
   - Check connection pool settings

2. **Authentication Failures**
   - Verify JWT secret is correctly set
   - Check token expiration settings
   - Ensure CORS is properly configured

3. **Deployment Failures**
   - Check service account permissions
   - Verify Docker image builds
   - Review Cloud Run logs

4. **Performance Issues**
   - Check database query performance
   - Review service resource limits
   - Monitor API rate limits

## Security Considerations

- All secrets in Secret Manager
- Service-to-service authentication
- HTTPS only for external traffic
- Regular security updates
- Dependency scanning in CI/CD

## Backup and Recovery

- Daily database backups
- Point-in-time recovery enabled
- Disaster recovery plan documented
- Regular restore testing

## Cost Optimization

- Use Cloud Run min instances = 0 for non-critical services
- Schedule workers only when needed
- Monitor and optimize database queries
- Use appropriate machine types

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest)
- Service-specific READMEs in `services/*/README.md`