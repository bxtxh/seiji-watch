# Diet Issue Tracker

Independent, open-source platform for tracking Diet issues as tickets.

## MVP Goal
Public release before July 22, 2025 (House of Councillors election)

## Architecture (MVP)
Simplified 3-service architecture for rapid development:
- **ingest-worker**: Data collection and STT processing
- **api-gateway**: API with embedded vector operations
- **web-frontend**: Next.js PWA

## Repository Structure
```
├── services/           # MVP Services
│   ├── ingest-worker/  # Scraper + STT processing (combines diet-scraper + stt-worker)
│   ├── api-gateway/    # API with embedded vector ops (includes vector-store functionality)
│   └── web-frontend/   # Next.js PWA frontend
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
# Install Python dependencies
poetry install

# Install frontend dependencies  
npm install

# Start local development environment
docker-compose up -d

# Run services
poetry run uvicorn api-gateway.main:app --reload  # API
npm run dev --workspace=services/web-frontend     # Frontend
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

## Project Status
🚧 **In Development** - MVP target: July 22, 2025