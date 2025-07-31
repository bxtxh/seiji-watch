# Diet Issue Tracker - Directory Structure

Last Updated: 2025-07-27

## Overview

The project follows a microservices architecture with a monorepo structure. Each service has its own directory with standardized organization.

## Root Structure

```
seiji-watch/
├── services/           # Microservices
├── shared/            # Shared code and models
├── infra/             # Infrastructure (Terraform)
├── scripts/           # Project-wide scripts
├── docs/              # Documentation
├── data/              # Static data files
├── CLAUDE.md          # AI agent instructions
├── README.md          # Project overview
└── docker-compose.yml # Local development setup
```

## Services Directory

All microservices follow a consistent structure:

```
services/
├── api-gateway/       # API integration and authentication
├── data-processor/    # Data normalization and LLM analysis
├── diet-scraper/      # Web scraping from Diet sites
├── stt-worker/        # Speech-to-text processing
├── vector-store/      # Embeddings and semantic search
├── notifications-worker/ # Email notifications
└── web-frontend/      # Next.js PWA frontend
```

### Service Structure Template

Each service follows this structure:

```
service-name/
├── src/               # Source code
│   ├── __init__.py
│   ├── main.py       # Entry point
│   └── modules/      # Service-specific modules
├── tests/            # Test files
│   ├── unit/         # Unit tests
│   └── integration/  # Integration tests
├── scripts/          # Service-specific scripts
├── docs/             # Service documentation
├── Dockerfile        # Container definition
├── pyproject.toml    # Python dependencies
├── pytest.ini        # Test configuration
└── README.md         # Service overview
```

## Documentation Structure

```
docs/
├── 00-overview/       # Project overview and roadmap
├── 01-specs/          # Specifications
│   ├── product/       # Product requirements
│   ├── technical/     # Technical specifications
│   └── ux-ui/         # UX/UI specifications
├── 02-legal/          # Legal documents
├── 03-project-mgmt/   # Project management
├── 04-guides/         # How-to guides
│   ├── testing/       # Testing guides
│   ├── setup/         # Setup guides
│   └── deployment/    # Deployment guides
├── 05-api/            # API documentation
├── 90-specialized/    # Specialized documentation
├── archive/           # Archived documents
├── operational/       # Operational procedures
├── security/          # Security documentation
└── test-cases/        # Test case documentation
```

## Shared Directory

```
shared/
├── src/
│   └── shared/
│       ├── clients/   # Shared API clients
│       ├── database/  # Database connections
│       ├── models/    # SQLAlchemy models
│       ├── types/     # Type definitions
│       └── utils/     # Utility functions
├── alembic/           # Database migrations
└── tests/             # Shared tests
```

## Infrastructure Directory

```
infra/
├── *.tf               # Terraform configurations
├── terraform.tfvars   # Variable values
└── terraform/         # Additional Terraform files
```

## Naming Conventions

- **Directories**: kebab-case (e.g., `api-gateway`, `web-frontend`)
- **Python files**: snake_case (e.g., `main.py`, `diet_scraper.py`)
- **TypeScript/React**: PascalCase for components, camelCase for utils
- **Documentation**: UPPERCASE.md for guides, kebab-case.md for specs

## Service Responsibilities

### api-gateway

- RESTful API endpoints
- JWT authentication
- Rate limiting
- Request routing

### data-processor

- Data normalization
- Entity extraction
- LLM-based analysis
- Issue categorization

### diet-scraper

- Web scraping Diet sites
- PDF/TXT processing
- NDL API integration
- Rate-limited crawling

### stt-worker

- Audio extraction (yt-dlp)
- Whisper transcription
- Quality validation
- Async processing

### vector-store

- Embedding generation
- Semantic search
- Topic clustering
- Similar bill detection

### notifications-worker

- Email notifications
- Subscription management
- Daily batch processing
- Event tracking

### web-frontend

- Next.js PWA
- Responsive UI
- Accessibility features
- Real-time updates

## Development Workflow

1. Each service can be developed independently
2. Shared code goes in `/shared`
3. Service-specific scripts in `service/scripts/`
4. Tests mirror source structure
5. Documentation in appropriate `/docs` subdirectory

## Notes

- The previous `ingest-worker` has been renamed to `data-processor`
- Functionality has been properly distributed to specialized services
- All services follow consistent naming and structure patterns
