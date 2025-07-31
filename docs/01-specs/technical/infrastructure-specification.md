# Infrastructure Specification - Diet Issue Tracker

## Overview

This document provides comprehensive infrastructure specifications for the Diet Issue Tracker platform, deployed on Google Cloud Platform (GCP) using Terraform Infrastructure as Code (IaC).

## Architecture Overview

### Service Architecture

The system follows a microservices architecture with three core services:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   API Gateway   │    │  Ingest Worker  │
│    (Next.js)    │◄──►│    (FastAPI)    │◄──►│    (Python)     │
│    Cloud Run    │    │   Cloud Run     │    │   Cloud Run     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    Airtable     │ Weaviate Cloud  │      Cloud Storage          │
│ (Structured)    │   (Vectors)     │    (Files/Audio)            │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### Data Architecture

**Structured Data (Airtable)**

- Bills (法案): Legislative bills and proposals
- Members (議員): Diet members with political affiliations
- Speeches (発言): Parliamentary speeches and statements
- Issues (課題): Policy issues extracted via LLM analysis
- Votes (投票): Voting records and outcomes
- Parties (政党): Political party information
- Meetings (会議): Parliamentary session data
- IssueTags (課題タグ): Issue classification tags
- IssueCategories (課題カテゴリ): 3-layer CAP-based categorization
- REST API integration with Personal Access Token (PAT) authentication

**Vector Data (Weaviate Cloud)**

- Speech embeddings and semantic search
- Natural language processing and similarity matching
- GraphQL API integration

**Binary Storage (Cloud Storage)**

- Audio files, PDFs, scraped content
- Static assets and media files

## Infrastructure Components

### 1. Google Cloud Run Services

#### API Gateway Service

- **Service Name**: `seiji-watch-api-gateway-dev`
- **Image**: `asia-northeast1-docker.pkg.dev/gen-lang-client-0458605339/seiji-watch-dev/api-gateway:latest`
- **Port**: 8000
- **Resources**:
  - CPU: 1 vCPU
  - Memory: 512Mi
- **Environment Variables**:
  - `AIRTABLE_PAT` (Personal Access Token, from Secret Manager)
  - `AIRTABLE_BASE_ID` (from Secret Manager)
  - `OPENAI_API_KEY` (from Secret Manager)
  - `WEAVIATE_API_KEY` (from Secret Manager)
  - `WEAVIATE_CLUSTER_URL` (from Secret Manager)
  - `GCS_BUCKET_NAME`
  - `ENVIRONMENT=dev`

#### Ingest Worker Service

- **Service Name**: `seiji-watch-ingest-worker-dev`
- **Image**: `asia-northeast1-docker.pkg.dev/gen-lang-client-0458605339/seiji-watch-dev/ingest-worker:latest`
- **Port**: 8080
- **Resources**:
  - CPU: 2 vCPU
  - Memory: 2Gi
- **Timeout**: 3600 seconds (1 hour)
- **Environment Variables**: Same as API Gateway plus:
  - `PUBSUB_TOPIC=seiji-watch-ingest-jobs-dev`

### 2. Container Registry

#### Artifact Registry

- **Repository**: `seiji-watch-dev`
- **Location**: `asia-northeast1`
- **Format**: Docker
- **Cleanup Policies**:
  - Delete versions older than 30 days
  - Keep minimum 10 recent versions

### 3. Secret Management

#### Google Secret Manager

All sensitive configuration managed through Secret Manager:

| Secret Name                            | Purpose                                       |
| -------------------------------------- | --------------------------------------------- |
| `seiji-watch-airtable-pat-dev`         | Airtable Personal Access Token authentication |
| `seiji-watch-airtable-base-id-dev`     | Airtable base identifier                      |
| `seiji-watch-openai-api-key-dev`       | OpenAI API authentication                     |
| `seiji-watch-weaviate-api-key-dev`     | Weaviate Cloud authentication                 |
| `seiji-watch-weaviate-cluster-url-dev` | Weaviate cluster endpoint                     |
| `seiji-watch-jwt-secret-dev`           | JWT token signing key                         |

### 4. Networking

#### VPC Configuration

- **Network**: `seiji-watch-vpc-dev`
- **Subnet**: `seiji-watch-subnet-dev`
  - Primary CIDR: `10.0.0.0/24`
  - Secondary CIDR: `10.1.0.0/24` (services-range)
- **Region**: `asia-northeast1`

#### VPC Access Connector

- **Name**: `seiji-watch-vpc-conn-dev`
- **IP Range**: `10.8.0.0/28`
- **Machine Type**: `e2-micro`
- **Throughput**: 200-300 Mbps

#### Firewall Rules

- **HTTP/HTTPS Access**: Ports 80, 443 from `0.0.0.0/0`
- **Internal Communication**: Ports 8000, 8080, 3000 from `10.0.0.0/8`
- **ICMP**: Internal network communication

### 5. Messaging & Queues

#### Pub/Sub Topics

- **Ingest Jobs**: `seiji-watch-ingest-jobs-dev`
- **Dead Letter**: `seiji-watch-dead-letter-dev`

#### Pub/Sub Subscriptions

- **Ingest Jobs Subscription**: `seiji-watch-ingest-jobs-sub-dev`
  - Acknowledgment deadline: 600 seconds
  - Message retention: 7 days
  - Dead letter policy: 5 max delivery attempts

### 6. Storage

#### Cloud Storage Buckets

- **Main Bucket**: `seiji-watch-dev-[random-suffix]`
  - Location: `asia-northeast1`
  - Storage class: Standard
  - Purpose: Application data, processed files
- **Temp Bucket**: `seiji-watch-temp-dev-[random-suffix]`
  - Location: `asia-northeast1`
  - Storage class: Standard
  - Purpose: Temporary processing files

### 7. Domain & SSL

#### Custom Domain Configuration

- **Domain**: `politics-watch.jp`
- **Cloud Run Mapping**: `politics-watch.jp` → `seiji-watch-api-gateway-dev`
- **SSL Certificate**: Google-managed automatic provisioning
- **DNS Records Required**:

  ```
  A Records:
  politics-watch.jp → 216.239.32.21
  politics-watch.jp → 216.239.34.21
  politics-watch.jp → 216.239.36.21
  politics-watch.jp → 216.239.38.21

  AAAA Records:
  politics-watch.jp → 2001:4860:4802:32::15
  politics-watch.jp → 2001:4860:4802:34::15
  politics-watch.jp → 2001:4860:4802:36::15
  politics-watch.jp → 2001:4860:4802:38::15
  ```

## IAM & Security

### Service Accounts

#### Cloud Run Service Account

- **Email**: `seiji-watch-cloud-run-dev@gen-lang-client-0458605339.iam.gserviceaccount.com`
- **Roles**:
  - `roles/secretmanager.secretAccessor`
  - `roles/cloudsql.client`
  - `roles/pubsub.editor`
  - `roles/storage.objectAdmin` (buckets)

#### GitHub Actions Service Account

- **Email**: `seiji-watch-github-actions-dev@gen-lang-client-0458605339.iam.gserviceaccount.com`
- **Roles**:
  - `roles/run.developer`
  - `roles/iam.serviceAccountUser`
  - `roles/storage.admin`
  - `roles/artifactregistry.writer`

### Security Configuration

- All secrets managed through Google Secret Manager
- Service-to-service authentication via service accounts
- Container images stored in private Artifact Registry
- Network isolation through VPC and firewall rules

## External Dependencies

### Airtable Integration

- **API Version**: v0
- **Authentication**: Personal Access Token (PAT) - replacing deprecated API keys
- **Base ID**: Stored in Secret Manager
- **Tables**:
  - Bills (法案): 20+ records with legislative proposals
  - Members (議員): 50+ records with complete political profiles
  - Speeches (発言): 100+ records with AI analysis metadata
  - Issues (課題): 70+ records with LLM-extracted policy issues
  - Votes (投票): Voting record data
  - Parties (政党): 8 active political parties
  - Meetings (会議): Parliamentary session metadata
  - IssueTags (課題タグ): Issue classification system
  - IssueCategories (課題カテゴリ): 3-layer CAP-based categorization
- **Rate Limiting**: 5 requests/second per base with 300ms spacing
- **Schema Management**: Custom fields added programmatically via metadata API

### Weaviate Cloud

- **Cluster URL**: Stored in Secret Manager
- **Authentication**: API Key
- **Schema**: Custom speech embeddings schema
- **Vector Dimensions**: OpenAI text-embedding-3-large (3072)

### OpenAI Integration

- **API Version**: v1
- **Models Used**:
  - `text-embedding-3-large` (embeddings)
  - `gpt-4` (content analysis)
- **Rate Limiting**: Tier-based

## Monitoring & Observability

### Logging

- **Platform**: Google Cloud Logging
- **Format**: Structured JSON logs
- **Retention**: 30 days (default)
- **Log Levels**: INFO, WARNING, ERROR, CRITICAL

### Metrics

- **Platform**: Google Cloud Monitoring
- **Key Metrics**:
  - Request latency (p50, p95, p99)
  - Error rates by service
  - Resource utilization (CPU, Memory)
  - Custom business metrics

### Health Checks

- **Endpoint**: `/health` (each service)
- **Frequency**: 10 seconds
- **Timeout**: 5 seconds
- **Unhealthy Threshold**: 3 consecutive failures

## Deployment

### Infrastructure as Code

- **Tool**: Terraform
- **Provider**: Google Cloud
- **State**: Local state (recommend migrating to Cloud Storage)
- **Configuration Files**:
  - `main.tf` - Core configuration
  - `cloud_run.tf` - Cloud Run services
  - `storage.tf` - Storage buckets
  - `iam.tf` - IAM and security
  - `external_services.tf` - External integrations

### CI/CD Pipeline

- **Platform**: GitHub Actions
- **Triggers**: Push to main branch
- **Steps**:
  1. Build container images
  2. Push to Artifact Registry
  3. Deploy to Cloud Run
  4. Run health checks

### Environment Management

- **Current**: Development environment (`dev`)
- **Future**: Staging (`staging`) and Production (`prod`) environments
- **Resource Naming**: `seiji-watch-{resource}-{environment}`

## Cost Optimization

### Resource Sizing

- **API Gateway**: Minimal resources for development workload
- **Ingest Worker**: Higher resources for data processing
- **Storage**: Standard class for active data

### Auto-scaling

- **Cloud Run**: Automatic scaling 0-1000 instances
- **Minimum Instances**: 0 (cost optimization)
- **Maximum Instances**: 1000 (sufficient for expected load)

## Disaster Recovery

### Backup Strategy

- **Airtable**: Vendor-managed backups
- **Weaviate Cloud**: Vendor-managed backups
- **Cloud Storage**: Multi-regional replication
- **Configuration**: Version-controlled in Git

### Recovery Procedures

1. **Service Outage**: Auto-restart via Cloud Run health checks
2. **Data Loss**: Restore from vendor backups
3. **Complete Infrastructure Loss**: Redeploy via Terraform

## Maintenance

### Regular Tasks

- **Weekly**: Monitor data collection pipeline health
- **Monthly**: Review and rotate secrets, analyze data quality metrics
- **Quarterly**: Update container base images, review Airtable schema changes
- **Bi-annually**: Review IAM permissions, optimize LLM analysis workflows
- **Annually**: Architecture review and optimization

### Update Procedures

1. Test changes in development environment
2. Update Terraform configuration
3. Apply changes via `terraform apply`
4. Verify service health
5. Update documentation

## Future Improvements

### Data Pipeline Enhancements

- Implement real-time Diet website scraping
- Add automated bill content analysis via LLM
- Integrate with national archives for historical data
- Develop speech-to-text pipeline for Diet TV audio

### Scalability Enhancements

- Migrate to PostgreSQL for complex queries and analytics
- Implement Redis caching layer for frequently accessed data
- Add load balancing for high availability
- Consider multi-region deployment for global access

### AI/ML Capabilities

- Implement GPT-4 integration for advanced content analysis
- Add automated issue categorization refinement
- Develop political sentiment analysis algorithms
- Create predictive models for legislative outcomes

### Security Hardening

- Implement network policies
- Add vulnerability scanning for containers
- Enable audit logging for data access
- Implement secret rotation automation

### Performance Optimization

- Implement CDN for static assets
- Add database connection pooling
- Optimize container images
- Implement service mesh for observability

### MVP Completion Tasks

- Deploy web frontend to Cloud Run
- Implement API authentication and rate limiting
- Add comprehensive error handling and monitoring
- Create data quality validation workflows

---

**Document Version**: 1.1  
**Last Updated**: July 12, 2025  
**Maintained By**: Engineering Team  
**Review Cycle**: Monthly

## Recent Updates (v1.1)

### EPIC 13 Completion (July 12, 2025)

- **Authentication Migration**: Updated from deprecated Airtable API keys to Personal Access Tokens (PAT)
- **Database Schema Established**: All 9 Airtable tables created with proper field schemas
- **Data Population Completed**:
  - 50 member records with complete political profiles
  - 100 speech records with AI analysis metadata
  - 70 issue records extracted via LLM analysis from legislative bills
  - 8 political party records with relationship mapping
- **Infrastructure Validation**: All table access permissions verified (100% success rate)
- **MVP Data Foundation**: Core database ready for frontend integration and API deployment
