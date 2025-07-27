# Diet Issue Tracker

Independent, open-source platform for tracking Diet issues as tickets.

## MVP Goal
Public release before July 22, 2025 (House of Councillors election)

<!-- ## Architecture (MVP) - OUTDATED: This was for the 3-service MVP architecture
Simplified 3-service architecture for rapid development:
- **ingest-worker**: Data collection and STT processing
- **api-gateway**: API with embedded vector operations
- **web-frontend**: Next.js PWA
-->

## Architecture
Microservices architecture with specialized components:
- **diet-scraper**: Data collection from Diet websites
- **stt-worker**: Speech-to-text processing
- **data-processor**: Data normalization and LLM analysis
- **vector-store**: Embedding generation and semantic search
- **api-gateway**: RESTful API with authentication
- **web-frontend**: Next.js PWA frontend
- **notifications-worker**: Email notification service

## Repository Structure
```
├── services/           # Microservices
│   ├── diet-scraper/   # Web scraping and data collection
│   ├── stt-worker/     # Speech-to-text processing with Whisper
│   ├── data-processor/ # Data normalization and LLM analysis
│   ├── vector-store/   # Embedding generation and vector search
│   ├── api-gateway/    # RESTful API gateway
│   ├── web-frontend/   # Next.js PWA frontend
│   └── notifications-worker/ # Email notification service
├── shared/             # Shared data models and utilities
├── infra/              # Infrastructure as code (Terraform)
├── docs/               # Documentation
└── scripts/            # Development and deployment scripts
```

## Tech Stack
- **Backend**: Python 3.11 + FastAPI + PostgreSQL + pgvector
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Infrastructure**: GCP (Cloud Run, Cloud SQL, Cloud Storage)
- **Package Management**: Poetry (Python) + npm workspaces (Node.js)

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Poetry

### Quick Start
```bash
# Install Python dependencies for all services
cd services && for dir in */; do (cd "$dir" && poetry install); done

# Install frontend dependencies  
cd services/web-frontend && npm install

# Start local development environment (PostgreSQL + pgvector)
docker-compose up -d

# Run services (from project root)
cd services/api-gateway && poetry run uvicorn src.main:app --reload  # API Gateway
cd services/web-frontend && npm run dev                             # Frontend

# Optional: Run other services as needed
cd services/diet-scraper && poetry run python -m src.main           # Diet Scraper
cd services/stt-worker && poetry run python -m src.main             # STT Worker
cd services/data-processor && poetry run python -m src.main         # Data Processor
cd services/vector-store && poetry run python -m src.main           # Vector Store
```

## Infrastructure Deployment

### Prerequisites for GCP Deployment
- GCP Project with billing enabled
- Terraform >= 1.0
- gcloud CLI authenticated

### Deploy to GCP
```bash
# 1. Copy and configure Terraform variables
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Edit infra/terraform.tfvars with your GCP project details

# 2. Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# 3. Deploy infrastructure
./scripts/terraform-deploy.sh -e dev -a apply

# 4. Update secrets in GCP Secret Manager
gcloud secrets versions add seiji-watch-openai-api-key-dev --data-file=- <<< 'your-openai-api-key'
```

### Infrastructure Components
- **Cloud SQL**: PostgreSQL 15 with pgvector extension
- **Cloud Run**: Serverless containers for API and worker services  
- **Artifact Registry**: Docker container registry
- **Cloud Storage**: File storage for raw and processed data
- **Secret Manager**: Secure API key and credential storage
- **Pub/Sub**: Asynchronous job processing queue
- **VPC**: Private networking with Cloud SQL access

## CI/CD Pipeline

### GitHub Actions Workflows
- **Main CI/CD**: Automated testing, building, and deployment on push to main
- **Pull Request Checks**: Code quality gates for all PRs
- **Infrastructure Management**: Terraform validation and deployment

### Required GitHub Secrets
Set these secrets in your GitHub repository settings:
```bash
GCP_PROJECT_ID=your-gcp-project-id
GCP_SA_KEY=<service-account-key-json>  # From Terraform output
ARTIFACT_REGISTRY_URL=asia-northeast1-docker.pkg.dev
```

### Development Workflow
1. Create feature branch from `main`
2. Make changes and commit with conventional commit format
3. Push branch - PR checks run automatically
4. Create PR - additional quality gates and security scans
5. Merge to `main` - automatic deployment to staging
6. Manual approval required for production deployment

### Environment Promotions
- **Staging**: Auto-deployed on main branch push
- **Production**: Manual approval gate via GitHub Environment protection

## Project Status
🚧 **In Development** - MVP target: July 22, 2025

### Development Progress
- ✅ **EPIC 0: Infrastructure Foundations** (5/5 completed - July 1, 2025)
  - Repository structure and monorepo setup
  - Local development environment (Docker + PostgreSQL + pgvector)
  - GCP infrastructure with Terraform (Cloud Run, Cloud SQL, Artifact Registry)
  - CI/CD pipeline with GitHub Actions
  - Shared data models with Alembic migrations

- 🎯 **Next: EPIC 1: Single Meeting Pipeline** (0/6 tickets)
  - Diet website scraper implementation
  - Speech-to-text integration
  - Data normalization pipeline
  - Vector embedding generation
  - Search API implementation
  - Basic frontend interface

### Milestones
- ✅ Infrastructure complete (3 days ahead of schedule)
- 🎯 Feature freeze: July 15, 2025 (14 days remaining)
- 🎯 MVP launch: July 22, 2025 (21 days remaining)