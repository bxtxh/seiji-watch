# Diet Issue Tracker - Developer Onboarding Guide

Welcome to the Diet Issue Tracker project! This guide will help you get started with development quickly and efficiently.

## 🎯 Project Overview

The Diet Issue Tracker is an open-source platform that tracks Japanese legislative issues, bills, and parliamentary discussions. It helps citizens understand and follow political developments through AI-powered analysis and categorization.

### Key Features
- Real-time tracking of Diet bills and their progress
- AI-powered issue extraction and categorization (CAP-based)
- Speech transcription and semantic search
- Progressive Web App with offline support
- Accessibility-focused design (WCAG compliant)

## 🏗️ Architecture

The project uses a microservices architecture with 7 services:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  diet-scraper   │────▶│  data-processor  │────▶│  vector-store   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   stt-worker    │     │   api-gateway    │◀────│  web-frontend   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │notifications-work│
                        └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (for backend services)
- **Node.js 18+** (for frontend)
- **Docker & Docker Compose** (for local development)
- **Poetry** (Python package manager)
- **Git** (version control)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/seiji-watch.git
cd seiji-watch
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.development .env

# Edit .env with your API keys:
# - OpenAI API key (required for LLM features)
# - Airtable PAT (required for data storage)
# - Weaviate API key (optional for local dev)
```

### 3. Start Local Development

```bash
# Start all services with Docker Compose
docker-compose up -d

# Or start individual services:
cd services/web-frontend
npm install
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
seiji-watch/
├── services/               # Microservices
│   ├── diet-scraper/      # Web scraping service
│   ├── stt-worker/        # Speech-to-text processing
│   ├── data-processor/    # Data normalization & LLM analysis
│   ├── vector-store/      # Embedding generation & search
│   ├── api-gateway/       # REST API & authentication
│   ├── web-frontend/      # Next.js PWA frontend
│   └── notifications/     # Email notification service
├── shared/                # Shared Python library
├── infra/                 # Terraform infrastructure
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── .github/               # CI/CD workflows
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feat/your-feature-name
```

### 2. Make Changes

Follow these guidelines:
- **Python**: PEP 8, type hints required, use Black formatter
- **TypeScript**: ESLint rules, proper types, no `any`
- **Tests**: Write tests for new features
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

### 3. Run Tests Locally

```bash
# Python services
cd services/api-gateway
poetry run pytest

# Frontend
cd services/web-frontend
npm run test
npm run lint
```

### 4. Submit Pull Request

- Create PR against `main` branch
- Fill out PR template
- Ensure CI checks pass
- Request review from team members

## 🛠️ Service-Specific Development

### Frontend (web-frontend)

```bash
cd services/web-frontend
npm install
npm run dev          # Start development server
npm run build        # Build for production
npm run test         # Run tests
npm run lint         # Run linting
```

Key technologies:
- Next.js 13+ (App Router)
- TypeScript
- Tailwind CSS
- PWA features

### API Gateway

```bash
cd services/api-gateway
poetry install
poetry run uvicorn src.main:app --reload  # Start dev server
poetry run pytest                          # Run tests
poetry run mypy .                          # Type checking
```

Key technologies:
- FastAPI
- JWT authentication
- Redis caching
- Rate limiting

### Data Processor

```bash
cd services/data-processor
poetry install
poetry run python -m src.main  # Run processor
```

Features:
- LLM-based analysis (OpenAI/Claude)
- Policy categorization (CAP)
- Airtable integration

## 📚 Key Concepts

### 1. Issue Categories (3-Layer CAP System)

```
L1: Major Topics (25 categories)
└── L2: Sub-Topics (200 categories)
    └── L3: Specific Policy Areas (500 areas)
```

### 2. Bill Workflow

```
Backlog → 審議中 (Under Review) → 採決待ち (Awaiting Vote) → 成立/否決
```

### 3. Data Sources

- **Diet Bill Pages**: HTML scraping
- **Transcripts**: PDF/TXT processing  
- **Diet TV**: HLS stream processing
- **NDL Minutes API**: Historical data

## 🔐 Security Considerations

1. **Never commit secrets** - Use environment variables
2. **API Authentication** - All API calls require JWT tokens
3. **Rate Limiting** - Respect external API limits
4. **Data Privacy** - Only public figure data is stored

## 🐛 Debugging Tips

### Common Issues

1. **Port conflicts**: Check if ports 3000, 8000, 5432, 6379 are free
2. **API connection errors**: Verify `.env` configuration
3. **Build failures**: Clear Docker cache with `docker-compose build --no-cache`
4. **Type errors**: Run `mypy` for Python, `npm run type-check` for TypeScript

### Useful Commands

```bash
# View logs
docker-compose logs -f [service-name]

# Reset database
docker-compose down -v
docker-compose up -d

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Run specific service
docker-compose up [service-name]
```

## 📖 Additional Resources

- [Technical Specifications](docs/01-specs/technical/)
- [API Documentation](docs/05-api/)
- [Configuration Guide](docs/90-specialized/configuration-management.md)
- [Testing Guide](docs/04-guides/testing/)
- [Deployment Guide](docs/deployment.md)

## 🤝 Getting Help

1. **Documentation**: Check `/docs` directory
2. **Code Comments**: Look for inline documentation
3. **Team Chat**: Join our Slack/Discord
4. **Issues**: Create GitHub issue with details

## 📋 Checklist for New Developers

- [ ] Environment setup complete
- [ ] Can run frontend locally
- [ ] Can run API gateway locally
- [ ] Understood service architecture
- [ ] Read coding standards
- [ ] Joined team communication channels
- [ ] Made first commit (even docs!)

## 🎉 Welcome Aboard!

We're excited to have you contribute to making Japanese politics more transparent and accessible. Happy coding!

---

*Last updated: 2025-01-27*