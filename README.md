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

## Project Status
🚧 **In Development** - MVP target: July 22, 2025