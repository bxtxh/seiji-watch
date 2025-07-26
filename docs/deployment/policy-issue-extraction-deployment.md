# Policy Issue Extraction System - Deployment Guide

## Overview

This guide covers the deployment of the dual-level policy issue extraction system across all components including enhanced issue extraction, Airtable integration, Discord notifications, and monitoring systems.

## Prerequisites

### Environment Requirements
- Python 3.11.2+
- Node.js 18+ (for API Gateway)
- PostgreSQL 14+ with pgvector extension
- Redis 6+ (for rate limiting and caching)
- Docker and Docker Compose (recommended for development)

### External Service Accounts
- OpenAI API key with GPT-4 access
- Airtable account with API access
- Discord webhook URL for notifications
- SendGrid account for email notifications (optional)

### Required Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=800
OPENAI_TEMPERATURE=0.2

# Airtable Configuration
AIRTABLE_PAT=keyXXX
AIRTABLE_BASE_ID=appXXX
AIRTABLE_ISSUES_TABLE=tblXXX
AIRTABLE_RATE_LIMIT_PER_SECOND=5

# Discord Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
DISCORD_NOTIFICATIONS_ENABLED=true
DISCORD_NOTIFICATION_TIME=14:00
DISCORD_TIMEZONE=Asia/Tokyo

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/seiji_watch
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_BASE_URL=https://api.seiji-watch.com
WEBHOOK_SECRET_KEY=your-webhook-secret

# Monitoring Configuration
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

## Component Deployment

### 1. Ingest Worker Service

The ingest worker contains the core policy issue extraction logic.

#### Installation

```bash
cd services/ingest-worker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install additional dependencies for Japanese NLP
pip install janome mecab-python3

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

#### Required Dependencies

```bash
# Core dependencies
pip install openai>=1.0.0
pip install airtable-python-wrapper>=0.15.0
pip install pydantic>=2.0.0
pip install asyncio>=3.4.3
pip install aiohttp>=3.8.0

# Japanese NLP dependencies  
pip install janome>=0.5.0
pip install mecab-python3>=1.0.6

# Testing dependencies
pip install pytest>=7.0.0
pip install pytest-asyncio>=0.21.0
pip install pytest-cov>=4.0.0
```

#### Service Configuration

```python
# config/extractor_config.py
from pydantic import BaseSettings

class ExtractorConfig(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 800
    openai_temperature: float = 0.2
    
    airtable_api_key: str
    airtable_base_id: str
    airtable_issues_table: str
    
    discord_webhook_url: str
    discord_notifications_enabled: bool = True
    
    class Config:
        env_file = ".env"
```

#### Running the Service

```bash
# Development mode
python -m src.services.policy_issue_extractor

# Production mode with gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8001 src.main:app

# With Docker
docker build -t seiji-watch/ingest-worker .
docker run -d --env-file .env -p 8001:8001 seiji-watch/ingest-worker
```

### 2. API Gateway Enhancement

The API gateway provides enhanced endpoints for dual-level issue management.

#### Installation

```bash
cd services/api-gateway

# Install Node.js dependencies
npm install

# Install additional dependencies
npm install fastapi uvicorn python-multipart

# Set up Python environment for enhanced routes
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Router Registration

Update `src/main.py` to include the new routes:

```python
# src/main.py
from fastapi import FastAPI
from routes.enhanced_issues import router as enhanced_issues_router
from routes.airtable_webhooks import router as webhooks_router
from routes.batch_management import router as batch_router
from routes.monitoring import router as monitoring_router

app = FastAPI(title="Seiji Watch API Gateway")

# Register enhanced routes
app.include_router(enhanced_issues_router, prefix="/api/issues", tags=["enhanced-issues"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(batch_router, prefix="/api/batch", tags=["batch"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])
```

#### Running the API Gateway

```bash
# Development mode
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.main:app --workers 4 --host 0.0.0.0 --port 8000

# With Docker
docker build -t seiji-watch/api-gateway .
docker run -d --env-file .env -p 8000:8000 seiji-watch/api-gateway
```

### 3. Discord Notification Bot

#### Service Configuration

```bash
cd services/ingest-worker

# Configure Discord bot
python -c "
from src.services.discord_notification_bot import DiscordNotificationBot
import asyncio

async def test_discord():
    bot = DiscordNotificationBot()
    await bot.send_test_notification()

asyncio.run(test_discord())
"
```

#### Scheduling with Cron

```bash
# Add to crontab for daily notifications at 14:00 JST
0 5 * * * cd /path/to/seiji-watch/services/ingest-worker && python -m src.services.discord_notification_bot
```

#### Scheduling with Cloud Functions (GCP)

```yaml
# cloud-function.yaml
name: discord-notifications
runtime: python311
entryPoint: send_daily_notification
schedule: "0 5 * * *"
timeZone: "Asia/Tokyo"
```

### 4. Database Setup

#### PostgreSQL Configuration

```sql
-- Create database
CREATE DATABASE seiji_watch;

-- Create user
CREATE USER seiji_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE seiji_watch TO seiji_user;

-- Enable pgvector extension
\c seiji_watch;
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Migration Scripts

```bash
cd shared

# Run Alembic migrations
alembic upgrade head

# Create new migration for policy issues enhancement
alembic revision --autogenerate -m "Add policy issue extraction enhancements"
```

### 5. Monitoring and Alerting Setup

#### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'seiji-watch-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/monitoring/metrics'
    
  - job_name: 'seiji-watch-ingest'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
```

#### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Policy Issue Extraction System",
    "panels": [
      {
        "title": "Issue Extraction Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(issues_extracted_total[5m])"
          }
        ]
      },
      {
        "title": "LLM API Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Airtable API Rate Limit Usage",
        "type": "singlestat",
        "targets": [
          {
            "expr": "airtable_rate_limit_remaining"
          }
        ]
      }
    ]
  }
}
```

#### Alert Rules

```yaml
# alerting-rules.yml
groups:
  - name: policy-issue-extraction
    rules:
      - alert: HighIssueExtractionFailureRate
        expr: rate(issues_extraction_failures_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High issue extraction failure rate"
          
      - alert: LLMAPIDown
        expr: up{job="llm-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "LLM API is down"
          
      - alert: AirtableRateLimitExceeded
        expr: airtable_rate_limit_remaining < 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Airtable rate limit nearly exceeded"
```

## Production Deployment

### 1. Container Orchestration

#### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ingest-worker:
    build: 
      context: ./services/ingest-worker
      dockerfile: Dockerfile.prod
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AIRTABLE_PAT=${AIRTABLE_PAT}
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    
  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile.prod
    ports:
      - "80:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - ingest-worker
      - postgres
      - redis
    restart: unless-stopped
    
  postgres:
    image: pgvector/pgvector:pg14
    environment:
      - POSTGRES_DB=seiji_watch
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
    
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  postgres_data:
  grafana_data:
```

#### Kubernetes Deployment

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: policy-issue-extraction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: policy-issue-extraction
  template:
    metadata:
      labels:
        app: policy-issue-extraction
    spec:
      containers:
      - name: ingest-worker
        image: seiji-watch/ingest-worker:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-api-key
        - name: AIRTABLE_PAT
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: airtable-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      - name: api-gateway
        image: seiji-watch/api-gateway:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "125m"
          limits:
            memory: "512Mi"
            cpu: "250m"
```

### 2. Cloud Deployment (GCP)

#### Cloud Run Deployment

```bash
# Build and push images
gcloud builds submit --tag gcr.io/PROJECT_ID/ingest-worker services/ingest-worker
gcloud builds submit --tag gcr.io/PROJECT_ID/api-gateway services/api-gateway

# Deploy to Cloud Run
gcloud run deploy ingest-worker \
  --image gcr.io/PROJECT_ID/ingest-worker \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY}

gcloud run deploy api-gateway \
  --image gcr.io/PROJECT_ID/api-gateway \
  --platform managed \
  --region us-central1 \
  --port 8000 \
  --allow-unauthenticated
```

#### Cloud Functions for Scheduled Tasks

```python
# cloud-function/main.py
import functions_framework
from services.discord_notification_bot import DiscordNotificationBot

@functions_framework.http
def send_daily_notification(request):
    """Cloud Function for daily Discord notifications."""
    bot = DiscordNotificationBot()
    result = await bot.send_daily_notification()
    return {"status": "success", "result": result}
```

```bash
# Deploy Cloud Function
gcloud functions deploy send-daily-notification \
  --runtime python311 \
  --trigger-http \
  --entry-point send_daily_notification \
  --set-env-vars DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}

# Set up Cloud Scheduler
gcloud scheduler jobs create http discord-daily-notification \
  --schedule "0 5 * * *" \
  --uri "https://us-central1-PROJECT_ID.cloudfunctions.net/send-daily-notification" \
  --http-method GET \
  --time-zone "Asia/Tokyo"
```

## Security Configuration

### 1. API Security

```python
# Security configuration
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://seiji-watch.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["api.seiji-watch.com", "*.seiji-watch.com"]
)

security = HTTPBearer()
```

### 2. Webhook Security

```python
# Webhook signature verification
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected_signature}")
```

### 3. Environment Security

```bash
# Use secrets management
export OPENAI_API_KEY=$(gcloud secrets versions access latest --secret="openai-api-key")
export AIRTABLE_PAT=$(gcloud secrets versions access latest --secret="airtable-api-key")

# Network security
gcloud compute firewall-rules create allow-api-gateway \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --target-tags api-gateway

# Enable VPC for internal communication
gcloud compute networks create seiji-watch-vpc --subnet-mode regional
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Indexes for enhanced performance
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_level ON issues(level);
CREATE INDEX idx_issues_source_bill ON issues(source_bill_id);
CREATE INDEX idx_issues_created_at ON issues(created_at);

-- Partial indexes for common queries
CREATE INDEX idx_issues_pending ON issues(status) WHERE status = 'pending';
CREATE INDEX idx_issues_approved_lv1 ON issues(level, status) WHERE level = 1 AND status = 'approved';
```

### 2. Caching Strategy

```python
# Redis caching configuration
import redis.asyncio as redis

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True,
    max_connections=20
)

# Cache frequently accessed data
async def get_cached_issues(level: int, status: str):
    cache_key = f"issues:{level}:{status}"
    cached_data = await redis_client.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    # Fetch from database
    data = await fetch_issues_from_db(level, status)
    
    # Cache for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(data))
    return data
```

### 3. Rate Limiting

```python
# Rate limiting configuration
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Initialize rate limiter
await FastAPILimiter.init(redis_client)

# Apply rate limits to endpoints
@app.get("/api/issues/extract")
@depends(RateLimiter(times=10, seconds=60))  # 10 requests per minute
async def extract_issues():
    pass
```

## Backup and Recovery

### 1. Database Backup

```bash
# Automated PostgreSQL backup
#!/bin/bash
BACKUP_DIR="/backup/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump -h localhost -U seiji_user seiji_watch > "$BACKUP_DIR/seiji_watch_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/seiji_watch_$DATE.sql"

# Upload to cloud storage
gsutil cp "$BACKUP_DIR/seiji_watch_$DATE.sql.gz" gs://seiji-watch-backups/postgres/
```

### 2. Configuration Backup

```bash
# Backup configuration and secrets
kubectl get secrets -o yaml > backup/secrets.yaml
kubectl get configmaps -o yaml > backup/configmaps.yaml

# Backup Airtable schema
python -c "
from services.airtable_issue_manager import AirtableIssueManager
manager = AirtableIssueManager()
schema = manager.export_table_schema()
with open('backup/airtable_schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
"
```

### 3. Disaster Recovery

```bash
# Recovery procedures
# 1. Restore database
gunzip seiji_watch_backup.sql.gz
psql -h localhost -U seiji_user seiji_watch < seiji_watch_backup.sql

# 2. Restore configuration
kubectl apply -f backup/secrets.yaml
kubectl apply -f backup/configmaps.yaml

# 3. Restart services
kubectl rollout restart deployment/policy-issue-extraction
```

## Health Checks and Monitoring

### 1. Health Check Endpoints

```python
# Health check implementation
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_health(),
        "redis": await check_redis_health(),
        "airtable": await check_airtable_health(),
        "openai": await check_openai_health()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### 2. Readiness and Liveness Probes

```yaml
# Kubernetes probes
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 3. Log Aggregation

```yaml
# Fluentd configuration for log aggregation
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/policy-issue-extraction*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
    </source>
    
    <match kubernetes.**>
      @type google_cloud
      project_id "#{ENV['PROJECT_ID']}"
    </match>
```

## Troubleshooting Guide

### Common Issues

1. **OpenAI API Rate Limits**
   - Monitor usage with `/api/monitoring/llm-usage`
   - Implement exponential backoff
   - Consider using multiple API keys

2. **Airtable Rate Limits**
   - Check rate limit headers
   - Implement request queuing
   - Monitor with `/api/monitoring/airtable-status`

3. **Discord Notification Failures**
   - Verify webhook URL validity
   - Check Discord server permissions
   - Review notification logs

4. **Database Performance Issues**
   - Monitor query performance
   - Check index usage
   - Review connection pool settings

### Debug Commands

```bash
# Check service status
kubectl get pods -l app=policy-issue-extraction

# View logs
kubectl logs -f deployment/policy-issue-extraction

# Connect to database
kubectl exec -it postgres-pod -- psql -U seiji_user seiji_watch

# Test API endpoints
curl -X GET "https://api.seiji-watch.com/api/issues/health"
curl -X GET "https://api.seiji-watch.com/api/monitoring/metrics"
```

## Maintenance Procedures

### 1. Routine Maintenance

```bash
# Weekly maintenance script
#!/bin/bash

# Update dependencies
pip install --upgrade -r requirements.txt

# Clean up old logs
find /var/log -name "*.log" -mtime +7 -delete

# Optimize database
psql -U seiji_user seiji_watch -c "VACUUM ANALYZE;"

# Clear old Redis cache
redis-cli FLUSHDB

# Restart services
docker-compose restart
```

### 2. Security Updates

```bash
# Security update checklist
# 1. Update base images
docker pull python:3.11-slim
docker pull node:18-alpine

# 2. Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image seiji-watch/ingest-worker:latest

# 3. Update dependencies
pip-audit
npm audit

# 4. Rotate secrets
gcloud secrets versions add openai-api-key --data-file=new-key.txt
```

This deployment guide provides comprehensive instructions for deploying, monitoring, and maintaining the policy issue extraction system in production environments.