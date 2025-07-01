# Diet Issue Tracker - Claude Code Memory

## Project Overview
- **Goal**: Independent, open-source platform tracking Diet issues as tickets
- **MVP Deadline**: July 22, 2025 (House of Councillors election)
- **Architecture**: Microservices with human + AI agent collaboration
- **Repository**: Monorepo structure with services/, shared/, infra/, docs/, scripts/

## Development Environment & Commands
- **Python**: Use `python3` (version 3.11.2)
- **Package Management**: Install via `python3 -m pip install package-name`
- **Testing**: Run tests with `python3 -m pytest` in each service directory
- **Linting**: Use `ruff check .` and `ruff format .` for Python code
- **Type Checking**: Run `mypy .` in each service directory

## Code Style & Standards
- **Python**: Follow PEP 8, use 4-space indentation
- **Imports**: Sort with `isort`, group stdlib/third-party/local
- **Type Hints**: Required for all function signatures
- **Documentation**: Use Google-style docstrings
- **Error Handling**: Explicit exception handling, avoid bare except
- **Security**: Never commit secrets, use environment variables

## Architecture Decisions
- **Microservices**: 6 services (diet-scraper, stt-worker, data-processor, vector-store, api-gateway, web-frontend)
- **Database**: PostgreSQL with pgvector for embeddings
- **Message Queue**: Cloud Pub/Sub for inter-service communication
- **API**: RESTful APIs with OpenAPI 3.0 specifications
- **Authentication**: JWT tokens via api-gateway
- **Infrastructure**: GCP (Cloud Run, Cloud SQL, Cloud Storage)

## Service-Specific Guidelines

### diet-scraper
- **Purpose**: Data collection from Diet websites
- **Tech Stack**: Python + requests + BeautifulSoup + Scrapy
- **Data Sources**: Diet bill pages (HTML), transcripts (TXT/PDF), Diet TV (HLS)
- **Rate Limiting**: Respect robots.txt, 1-2 second delays between requests
- **Error Handling**: Retry logic with exponential backoff
- **Data Validation**: WER ≤15% for speech recognition

### stt-worker
- **Purpose**: Speech-to-text processing
- **Tech Stack**: Python + yt-dlp + OpenAI Whisper
- **Model**: Whisper large-v3 for Japanese
- **Processing**: Async job processing via message queue
- **Storage**: Raw audio in Cloud Storage, transcripts in PostgreSQL

### data-processor
- **Purpose**: Data normalization, entity extraction, and LLM-based content analysis
- **Tech Stack**: Python + pandas + NLP libraries + OpenAI API/Claude API
- **Entities**: {Issue, Bill, Stage, Party, Member, Vote}
- **Workflow**: Backlog → 審議中 → 採決待ち → 成立
- **Categories**: 予算・決算, 税制, 社会保障, 外交・国際, 経済・産業, その他
- **LLM Analysis Features**:
  - Dynamic issue extraction from bill content using LLM
  - Parliamentary debate content analysis and topic modeling
  - Automatic bill-to-debate content linking based on semantic similarity
  - Current political issue trend analysis from aggregated content
  - Bill social impact assessment using multi-factor LLM evaluation
  - Cross-reference analysis between related bills and policy discussions
  - Temporal tracking of political agenda shifts and emerging issues

### vector-store
- **Purpose**: Embedding generation, vector search, and semantic analysis
- **Tech Stack**: Python + pgvector + sentence-transformers + OpenAI embeddings
- **Embeddings**: Japanese-optimized models (multilingual-E5, OpenAI text-embedding-3-large)
- **Indexing**: Incremental updates for new content
- **Advanced Search Features**:
  - Semantic similarity search between bills and debates
  - Issue-based clustering and topic discovery
  - Cross-temporal policy evolution tracking
  - Similar bill recommendation system
  - Political stance analysis through embedding space geometry

### api-gateway
- **Purpose**: API integration, authentication, rate limiting
- **Tech Stack**: FastAPI + Redis + JWT
- **CORS**: Configure for frontend domain
- **Rate Limiting**: Per-user and per-endpoint limits

### web-frontend
- **Purpose**: PWA frontend with accessibility focus and intelligent analysis features
- **Tech Stack**: Next.js + TypeScript + Tailwind CSS
- **Design**: Mobile-first, color-blind friendly palette (#27AE60/#C0392B/#F1C40F)
- **Accessibility**: ARIA labels, furigana toggle, keyboard navigation
- **Performance**: Mobile load ≤200ms, Lighthouse scores >90
- **Intelligence Features**:
  - Issue trend dashboard with LLM-generated insights
  - Bill impact visualization and analysis summaries
  - Semantic search interface for bill and debate content
  - Personalized bill recommendations based on user interests
  - Real-time political agenda tracking and alerts

## Data & Legal Compliance
- **Copyright**: Speech under Article 40, link to videos, code under MIT
- **Privacy**: Minimal PII (only public figures), no personal data storage
- **Election Law**: Maintain neutrality, no endorsements, no donations
- **Data Retention**: Define clear policies for audio/transcript storage

## Development Workflow
- **Branching**: Feature branches from main, PR required
- **Commits**: Conventional Commits format
- **Reviews**: Human review required for AI-generated code
- **Testing**: Unit tests + integration tests + E2E tests
- **CI/CD**: GitHub Actions with lint/test/accessibility gates
- **Deployment**: Blue-green deployment strategy

## AI Agent Collaboration
- **Service Assignment**: One AI agent per microservice when possible
- **API Contracts**: Define OpenAPI specs before implementation
- **Communication**: Async messaging between services
- **Testing**: Mock external dependencies for isolated testing
- **Documentation**: Update this file when making architectural changes
- **Web Research**: When web research involves complex judgments or abstract questions, consult with o3 via MCP

## Troubleshooting
- **Environment Issues**: Use Docker for consistent development environment
- **Database Issues**: Check PostgreSQL connection and pgvector extension
- **API Issues**: Verify service health endpoints and logging
- **Frontend Issues**: Check console for JavaScript errors and network requests

## Monitoring & Observability
- **Logging**: Structured JSON logs with Cloud Logging
- **Metrics**: Track p95 latency, error rates, data processing times
- **Alerts**: Set up for service failures and data pipeline issues
- **SLOs**: Define and monitor service level objectives

## Quick References
- **Diet Website**: https://www.sangiin.go.jp/
- **API Docs**: Located in docs/api/ for each service
- **Architecture Diagram**: docs/architecture.md
- **Deployment Guide**: docs/deployment.md

---
*Last updated: 2025-06-30*
*Update this file when making significant changes to project structure or decisions*