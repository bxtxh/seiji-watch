# Policy Issue Extraction System - Monitoring and Incident Response Playbook

## Overview

This playbook provides comprehensive monitoring procedures, alerting configurations, and incident response protocols for the dual-level policy issue extraction system.

## System Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Ingest Worker  │────│   Airtable API  │
│  (FastAPI)      │    │   (Python)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │    OpenAI API   │    │ Discord Webhook │
│   (Database)    │    │   (GPT-4)       │    │ (Notifications) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Performance Indicators (KPIs)

### Primary Metrics

1. **Issue Extraction Success Rate**
   - Target: > 95%
   - Measurement: Successful extractions / Total extraction attempts

2. **LLM Response Time**
   - Target: < 5 seconds (95th percentile)
   - Measurement: Time from API request to response

3. **Airtable API Success Rate**
   - Target: > 99%
   - Measurement: Successful API calls / Total API calls

4. **Daily Issue Review Queue Size**
   - Target: < 50 pending issues
   - Measurement: Count of issues with status = 'pending'

### Secondary Metrics

1. **Issue Quality Score**
   - Target: > 0.8 average
   - Measurement: Average quality score of approved issues

2. **Discord Notification Delivery Rate**
   - Target: > 95%
   - Measurement: Successful notifications / Total scheduled notifications

3. **API Response Time**
   - Target: < 500ms (95th percentile)
   - Measurement: API endpoint response times

4. **System Uptime**
   - Target: > 99.5%
   - Measurement: Total uptime / Total time

## Monitoring Infrastructure

### 1. Prometheus Metrics Collection

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "policy_issue_extraction_rules.yml"

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/monitoring/metrics'
    scrape_interval: 10s
    
  - job_name: 'ingest-worker'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['localhost:9187']
      
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
```

### 2. Custom Metrics Implementation

```python
# services/ingest-worker/src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
ISSUE_EXTRACTION_TOTAL = Counter(
    'issues_extracted_total',
    'Total number of issues extracted',
    ['level', 'status']
)

ISSUE_EXTRACTION_DURATION = Histogram(
    'issue_extraction_duration_seconds',
    'Time spent extracting issues',
    ['level']
)

LLM_REQUEST_DURATION = Histogram(
    'llm_request_duration_seconds',
    'Duration of LLM API requests',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

AIRTABLE_API_CALLS = Counter(
    'airtable_api_calls_total',
    'Total Airtable API calls',
    ['method', 'status']
)

AIRTABLE_RATE_LIMIT_REMAINING = Gauge(
    'airtable_rate_limit_remaining',
    'Remaining Airtable API rate limit'
)

PENDING_ISSUES_GAUGE = Gauge(
    'pending_issues_total',
    'Number of issues pending review'
)

DISCORD_NOTIFICATIONS = Counter(
    'discord_notifications_total',
    'Total Discord notifications sent',
    ['status']
)

class MetricsCollector:
    """Collect and expose custom metrics."""
    
    def __init__(self, port: int = 8001):
        self.port = port
        
    def start_metrics_server(self):
        """Start the metrics server."""
        start_http_server(self.port)
        
    def record_extraction_attempt(self, level: int, success: bool):
        """Record an issue extraction attempt."""
        status = 'success' if success else 'failure'
        ISSUE_EXTRACTION_TOTAL.labels(level=level, status=status).inc()
        
    def record_extraction_duration(self, level: int, duration: float):
        """Record extraction duration."""
        ISSUE_EXTRACTION_DURATION.labels(level=level).observe(duration)
        
    def record_llm_request(self, duration: float):
        """Record LLM API request duration."""
        LLM_REQUEST_DURATION.observe(duration)
        
    def record_airtable_request(self, method: str, success: bool):
        """Record Airtable API request."""
        status = 'success' if success else 'failure'
        AIRTABLE_API_CALLS.labels(method=method, status=status).inc()
        
    def update_airtable_rate_limit(self, remaining: int):
        """Update Airtable rate limit gauge."""
        AIRTABLE_RATE_LIMIT_REMAINING.set(remaining)
        
    def update_pending_issues_count(self, count: int):
        """Update pending issues count."""
        PENDING_ISSUES_GAUGE.set(count)
        
    def record_discord_notification(self, success: bool):
        """Record Discord notification attempt."""
        status = 'success' if success else 'failure'
        DISCORD_NOTIFICATIONS.labels(status=status).inc()
```

### 3. Health Check Endpoints

```python
# services/api-gateway/src/routes/monitoring.py
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    
    health_checks = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "components": {}
    }
    
    # Check database connectivity
    try:
        db_start = time.time()
        await check_database_connection()
        db_duration = time.time() - db_start
        health_checks["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_duration * 1000, 2)
        }
    except Exception as e:
        health_checks["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_checks["status"] = "unhealthy"
    
    # Check Redis connectivity
    try:
        redis_start = time.time()
        await check_redis_connection()
        redis_duration = time.time() - redis_start
        health_checks["components"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round(redis_duration * 1000, 2)
        }
    except Exception as e:
        health_checks["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_checks["status"] = "unhealthy"
    
    # Check Airtable API
    try:
        airtable_start = time.time()
        await check_airtable_connectivity()
        airtable_duration = time.time() - airtable_start
        health_checks["components"]["airtable"] = {
            "status": "healthy",
            "response_time_ms": round(airtable_duration * 1000, 2)
        }
    except Exception as e:
        health_checks["components"]["airtable"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_checks["status"] = "unhealthy"
    
    # Check OpenAI API
    try:
        openai_start = time.time()
        await check_openai_connectivity()
        openai_duration = time.time() - openai_start
        health_checks["components"]["openai"] = {
            "status": "healthy",
            "response_time_ms": round(openai_duration * 1000, 2)
        }
    except Exception as e:
        health_checks["components"]["openai"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_checks["status"] = "unhealthy"
    
    status_code = 200 if health_checks["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_checks)

@router.get("/metrics/summary")
async def metrics_summary():
    """Get key metrics summary."""
    
    # Get metrics from last 24 hours
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    summary = {
        "timestamp": end_time.isoformat(),
        "period": "24h",
        "metrics": {
            "total_extractions": await get_total_extractions(start_time, end_time),
            "success_rate": await get_extraction_success_rate(start_time, end_time),
            "avg_llm_response_time": await get_avg_llm_response_time(start_time, end_time),
            "pending_issues_count": await get_pending_issues_count(),
            "airtable_rate_limit_remaining": await get_airtable_rate_limit(),
            "discord_notifications_sent": await get_discord_notifications_sent(start_time, end_time)
        }
    }
    
    return summary

@router.get("/alerts/active")
async def active_alerts():
    """Get currently active alerts."""
    
    alerts = []
    
    # Check for high failure rate
    failure_rate = await get_recent_failure_rate()
    if failure_rate > 0.05:  # 5% threshold
        alerts.append({
            "alert": "HighFailureRate",
            "severity": "warning",
            "value": failure_rate,
            "threshold": 0.05,
            "description": "Issue extraction failure rate is above 5%"
        })
    
    # Check for slow LLM responses
    avg_llm_time = await get_avg_llm_response_time()
    if avg_llm_time > 10.0:  # 10 second threshold
        alerts.append({
            "alert": "SlowLLMResponse",
            "severity": "warning",
            "value": avg_llm_time,
            "threshold": 10.0,
            "description": "LLM response time is above 10 seconds"
        })
    
    # Check for high pending issue count
    pending_count = await get_pending_issues_count()
    if pending_count > 100:
        alerts.append({
            "alert": "HighPendingIssues",
            "severity": "warning",
            "value": pending_count,
            "threshold": 100,
            "description": "High number of issues pending review"
        })
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "active_alerts": alerts,
        "alert_count": len(alerts)
    }
```

## Alert Rules and Thresholds

### 1. Prometheus Alert Rules

```yaml
# policy_issue_extraction_rules.yml
groups:
  - name: policy_issue_extraction
    interval: 30s
    rules:
      # High-priority alerts
      - alert: SystemDown
        expr: up{job=~"api-gateway|ingest-worker"} == 0
        for: 1m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "{{ $labels.job }} service is down"
          description: "Service {{ $labels.job }} has been down for more than 1 minute"
          
      - alert: HighErrorRate
        expr: rate(issues_extracted_total{status="failure"}[5m]) / rate(issues_extracted_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "High issue extraction error rate"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
          
      - alert: LLMAPIDown
        expr: llm_request_duration_seconds_count == 0
        for: 5m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "LLM API appears to be down"
          description: "No LLM requests completed in the last 5 minutes"
          
      # Medium-priority alerts  
      - alert: SlowLLMResponses
        expr: histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[10m])) > 10
        for: 10m
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "LLM API responses are slow"
          description: "95th percentile response time is {{ $value }}s"
          
      - alert: AirtableRateLimitHigh
        expr: airtable_rate_limit_remaining < 50
        for: 1m
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "Airtable rate limit usage is high"
          description: "Only {{ $value }} requests remaining in rate limit window"
          
      - alert: HighPendingIssues
        expr: pending_issues_total > 100
        for: 30m
        labels:
          severity: warning
          team: content
        annotations:
          summary: "High number of issues pending review"
          description: "{{ $value }} issues are currently pending review"
          
      # Low-priority alerts
      - alert: DiscordNotificationFailures
        expr: rate(discord_notifications_total{status="failure"}[1h]) > 0.05
        for: 1h
        labels:
          severity: info
          team: engineering
        annotations:
          summary: "Discord notification failures detected"
          description: "{{ $value | humanizePercentage }} of Discord notifications are failing"
          
      - alert: LowIssueQuality
        expr: avg_over_time(issue_quality_score_avg[6h]) < 0.7
        for: 6h
        labels:
          severity: info
          team: content
        annotations:
          summary: "Issue quality scores are declining"
          description: "Average quality score is {{ $value }} over the last 6 hours"
```

### 2. Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@seiji-watch.com'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
    - match:
        team: content
      receiver: 'content-team'
    - match:
        team: engineering
      receiver: 'engineering-team'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/webhook'
        
  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@seiji-watch.com'
        subject: 'CRITICAL: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts-critical'
        title: 'Critical Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          {{ .Annotations.summary }}
          {{ .Annotations.description }}
          {{ end }}
          
  - name: 'engineering-team'
    email_configs:
      - to: 'engineering@seiji-watch.com'
        subject: 'Alert: {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#engineering-alerts'
        
  - name: 'content-team'
    email_configs:
      - to: 'content@seiji-watch.com'
        subject: 'Content Alert: {{ .GroupLabels.alertname }}'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#content-alerts'
```

## Incident Response Procedures

### Severity Levels

**Critical (P0)**: System completely down or major functionality broken
- Response time: 15 minutes
- Communication: Immediate

**High (P1)**: Significant functionality impaired 
- Response time: 1 hour
- Communication: Within 30 minutes

**Medium (P2)**: Minor functionality issues
- Response time: 4 hours
- Communication: Within 2 hours

**Low (P3)**: Enhancement requests or cosmetic issues
- Response time: 24 hours
- Communication: Next business day

### Critical Incident Response (P0)

#### 1. System Down
**Symptoms**: Health checks failing, no API responses
**Response Steps**:
```bash
# 1. Check service status
kubectl get pods -l app=policy-issue-extraction
docker-compose ps

# 2. Check logs
kubectl logs -f deployment/api-gateway --tail=100
kubectl logs -f deployment/ingest-worker --tail=100

# 3. Check external dependencies
curl -I https://api.openai.com/v1/models
curl -I https://api.airtable.com/v0/meta/bases

# 4. Restart services if needed
kubectl rollout restart deployment/api-gateway
kubectl rollout restart deployment/ingest-worker

# 5. Verify recovery
curl https://api.seiji-watch.com/api/issues/health
```

#### 2. High Error Rate
**Symptoms**: >10% of issue extractions failing
**Response Steps**:
```bash
# 1. Check recent error logs
kubectl logs deployment/ingest-worker | grep ERROR | tail -20

# 2. Check LLM API status
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# 3. Check Airtable API status
curl -H "Authorization: Bearer $AIRTABLE_PAT" \
  https://api.airtable.com/v0/$AIRTABLE_BASE_ID

# 4. Monitor metrics dashboard
open http://grafana:3000/d/policy-issues

# 5. Implement circuit breaker if needed
kubectl patch deployment ingest-worker -p '{"spec":{"template":{"spec":{"containers":[{"name":"ingest-worker","env":[{"name":"CIRCUIT_BREAKER_ENABLED","value":"true"}]}]}}}}'
```

### High Priority Incident Response (P1)

#### 1. Slow LLM Responses
**Symptoms**: >10 second response times from OpenAI
**Response Steps**:
```bash
# 1. Check OpenAI status page
curl https://status.openai.com/api/v2/status.json

# 2. Monitor request patterns
grep "llm_request_duration" /var/log/metrics.log | tail -20

# 3. Implement request throttling
kubectl set env deployment/ingest-worker LLM_REQUEST_THROTTLE=true

# 4. Consider model fallback
kubectl set env deployment/ingest-worker OPENAI_MODEL=gpt-3.5-turbo-16k
```

#### 2. Airtable Rate Limit Issues
**Symptoms**: Airtable API calls failing with 429 status
**Response Steps**:
```bash
# 1. Check current rate limit status
curl -H "Authorization: Bearer $AIRTABLE_PAT" \
  https://api.airtable.com/v0/$AIRTABLE_BASE_ID/Issues | grep -i rate

# 2. Enable rate limiting
kubectl set env deployment/ingest-worker AIRTABLE_RATE_LIMIT_ENABLED=true

# 3. Reduce request frequency
kubectl set env deployment/ingest-worker AIRTABLE_BATCH_SIZE=5
kubectl set env deployment/ingest-worker AIRTABLE_DELAY_MS=1000

# 4. Monitor recovery
watch 'curl -s https://api.seiji-watch.com/api/monitoring/airtable-status'
```

### Escalation Procedures

#### Engineering Escalation Path
1. **On-call Engineer** (Primary response)
2. **Senior Engineer** (If unresolved in 30 minutes)
3. **Engineering Manager** (If unresolved in 1 hour)
4. **CTO** (For extended outages)

#### Contact Information
```yaml
contacts:
  on_call: 
    slack: "@oncall-engineer"
    phone: "+1-555-0123"
  senior_engineer:
    slack: "@senior-eng"
    email: "senior@seiji-watch.com"
  eng_manager:
    slack: "@eng-manager"
    email: "manager@seiji-watch.com"
```

## Runbooks

### Daily Operations

#### Morning Health Check (9:00 AM JST)
```bash
#!/bin/bash
# Daily health check script

echo "=== Daily Health Check $(date) ==="

# 1. Check service status
kubectl get pods -l app=policy-issue-extraction

# 2. Check yesterday's metrics
curl -s "https://api.seiji-watch.com/api/monitoring/daily-summary" | jq

# 3. Check pending issues count
PENDING_COUNT=$(curl -s "https://api.seiji-watch.com/api/issues/pending/count" | jq -r '.pending_count')
echo "Pending issues: $PENDING_COUNT"

if [ $PENDING_COUNT -gt 50 ]; then
    echo "⚠️  High pending count detected"
    # Send notification to content team
    curl -X POST $SLACK_WEBHOOK_URL -d "{\"text\":\"High pending issues: $PENDING_COUNT\"}"
fi

# 4. Check Discord notification status
DISCORD_STATUS=$(curl -s "https://api.seiji-watch.com/api/monitoring/discord-status" | jq -r '.last_notification_status')
echo "Discord status: $DISCORD_STATUS"

# 5. Generate daily report
python scripts/generate_daily_report.py --date=$(date +%Y-%m-%d)
```

#### Weekly Maintenance (Sunday 2:00 AM JST)
```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly Maintenance $(date) ==="

# 1. Database maintenance
kubectl exec postgres-pod -- psql -U seiji_user seiji_watch -c "VACUUM ANALYZE;"

# 2. Clear old logs
kubectl exec api-gateway-pod -- find /var/log -name "*.log" -mtime +7 -delete

# 3. Update metrics retention
curl -X POST "http://prometheus:9090/api/v1/admin/tsdb/delete_series?match[]={__name__=~'.*'}&start=$(date -d '30 days ago' -u +%Y-%m-%dT%H:%M:%SZ)"

# 4. Generate weekly report
python scripts/generate_weekly_report.py

# 5. Backup configuration
kubectl get secrets -o yaml > backup/secrets-$(date +%Y%m%d).yaml
kubectl get configmaps -o yaml > backup/configmaps-$(date +%Y%m%d).yaml
```

### Disaster Recovery

#### Data Loss Recovery
```bash
#!/bin/bash
# Data recovery procedure

echo "=== Data Recovery $(date) ==="

# 1. Stop all services
kubectl scale deployment api-gateway --replicas=0
kubectl scale deployment ingest-worker --replicas=0

# 2. Restore database from backup
LATEST_BACKUP=$(gsutil ls gs://seiji-watch-backups/postgres/ | tail -1)
gsutil cp $LATEST_BACKUP /tmp/restore.sql.gz
gunzip /tmp/restore.sql.gz

kubectl exec postgres-pod -- dropdb seiji_watch
kubectl exec postgres-pod -- createdb seiji_watch
kubectl cp /tmp/restore.sql postgres-pod:/tmp/
kubectl exec postgres-pod -- psql -U seiji_user seiji_watch -f /tmp/restore.sql

# 3. Restore configuration
kubectl apply -f backup/secrets-latest.yaml
kubectl apply -f backup/configmaps-latest.yaml

# 4. Restart services
kubectl scale deployment api-gateway --replicas=3
kubectl scale deployment ingest-worker --replicas=2

# 5. Verify recovery
sleep 60
curl https://api.seiji-watch.com/api/issues/health
```

## Performance Monitoring

### Key Dashboards

#### 1. System Overview Dashboard
- Service uptime and health status
- Request rate and error rate trends
- Resource utilization (CPU, memory, disk)
- External API status (OpenAI, Airtable)

#### 2. Issue Extraction Dashboard
- Extraction success rate by level
- LLM response time distribution
- Issue quality score trends
- Pending issues backlog

#### 3. API Performance Dashboard
- Endpoint response times
- Request volume by endpoint
- Rate limiting status
- Cache hit rates

### Grafana Queries

```promql
# Extraction success rate
(rate(issues_extracted_total{status="success"}[5m]) / rate(issues_extracted_total[5m])) * 100

# 95th percentile LLM response time
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))

# API request rate
rate(http_requests_total[5m])

# Pending issues trend
pending_issues_total

# Airtable rate limit usage
(300 - airtable_rate_limit_remaining) / 300 * 100
```

This monitoring playbook provides comprehensive coverage for maintaining the health and performance of the policy issue extraction system.