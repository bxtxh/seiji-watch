# Development Tickets - Diet Issue Tracker MVP
*Based on o3 strategic recommendations with architecture considerations*

## Strategic Approach

### Core Philosophy
- **Vertical Slices**: End-to-end features over horizontal layers
- **Pragmatic Architecture**: Simplified services for MVP with migration path
- **Risk Mitigation**: Early deployment, continuous integration, scope freeze
- **Timeline**: 3 weeks to July 22, 2025 with July 15 feature freeze

### Service Architecture (MVP → Future)
**MVP (3 Services):**
- `ingest-worker`: Scraper + STT processing
- `api-gateway`: FastAPI with embedded vector operations
- `web-frontend`: Next.js PWA

**Post-MVP Migration Path:**
- Split vector operations to dedicated `vector-store` service
- Add separate `data-processor` service for complex analysis
- Implement `stt-worker` as independent service

## Ticket Breakdown (19 Tickets)

### EPIC 0: Infrastructure Foundations
**Target: July 4, 2025**

#### T00 - Repository Structure Setup
**Priority:** P0 | **Estimate:** 4 hours
- Monorepo structure with workspaces
- Poetry for Python dependency management
- Package.json with workspaces for frontend
- Basic .gitignore and README updates
**DoD:** All services have proper dependency management, repo structure matches architecture

#### T01 - Local Development Environment
**Priority:** P0 | **Estimate:** 6 hours
- Docker Compose with PostgreSQL 15 + pgvector
- Adminer for database management
- Volume mounts for persistent development data
- Environment variables template
**DoD:** `docker-compose up` starts complete local environment

#### T02 - GCP Infrastructure Bootstrap
**Priority:** P0 | **Estimate:** 8 hours
- Terraform configuration for GCP resources
- Cloud SQL (PostgreSQL + pgvector extension)
- Cloud Run services (3 services)
- Artifact Registry for container images
- Cloud Storage bucket for raw files
**DoD:** Infrastructure provisioned via `terraform apply`

#### T03 - CI/CD Pipeline Foundation
**Priority:** P0 | **Estimate:** 6 hours
- GitHub Actions workflow for testing
- Docker build and push to Artifact Registry
- Auto-deployment to Cloud Run on main branch
- Environment-specific deployments (staging/prod)
**DoD:** Push to main automatically deploys to staging environment

#### T04 - Shared Data Models
**Priority:** P0 | **Estimate:** 4 hours
- Pydantic models for Meeting, Speech, Member, Bill
- Database schema with migrations (Alembic)
- Shared types package for cross-service communication
**DoD:** Models are importable across services, migrations run successfully

---

### EPIC 1: Vertical Slice #1 - "Single Meeting Pipeline"
**Target: July 8, 2025**

#### T10 - Diet Website Scraper (Single Meeting)
**Priority:** P0 | **Estimate:** 8 hours
- Fetch HTML/PDF for specific meeting ID
- Parse meeting metadata and participant list
- Store raw files in Cloud Storage
- Basic error handling and logging
**DoD:** Can successfully scrape and store one complete meeting

#### T11 - Speech-to-Text Integration
**Priority:** P0 | **Estimate:** 6 hours
- OpenAI Whisper API integration
- Audio file processing from stored meeting data
- JSON transcript generation and storage
- Cost optimization (batch processing)
**DoD:** Audio converts to accurate Japanese transcript via API

#### T12 - Data Normalization Pipeline
**Priority:** P0 | **Estimate:** 8 hours
- Split transcripts into individual speeches
- Speaker identification and matching
- PostgreSQL storage with proper indexing
- Basic data validation and cleanup
**DoD:** Raw transcript becomes structured speech records in database

#### T13 - Vector Embedding Generation
**Priority:** P0 | **Estimate:** 6 hours
- OpenAI text-embedding-3-small integration
- Batch embedding generation for speeches
- pgvector storage with efficient indexing
- **Architecture Note:** Embedded in API service with clear separation for future extraction
**DoD:** All speeches have vector representations stored in pgvector

#### T14 - Search API Implementation
**Priority:** P0 | **Estimate:** 8 hours
- Hybrid search: keyword (PostgreSQL) + vector (pgvector)
- RESTful endpoints with proper pagination
- Result ranking and relevance scoring
- **Future-Proofing:** Abstract vector operations into separate module
**DoD:** API returns ranked search results combining text and semantic search

#### T15 - Basic Frontend Interface
**Priority:** P0 | **Estimate:** 10 hours
- Next.js setup with TypeScript
- Search interface with real-time results
- Speech detail modal with speaker info
- Mobile-responsive design foundation
**DoD:** Users can search and view meeting content through web interface

---

### EPIC 2: Vertical Slice #2 - "Multi-Meeting Automation"
**Target: July 12, 2025**

#### T20 - Automated Ingestion Scheduler
**Priority:** P1 | **Estimate:** 6 hours
- Cloud Scheduler → Pub/Sub → ingest-worker trigger
- Nightly batch processing of new meetings
- Status tracking and error notifications
**DoD:** System automatically processes new Diet meetings daily

#### T21 - Scraper Resilience & Optimization
**Priority:** P1 | **Estimate:** 6 hours
- Duplicate detection and skipping
- Exponential backoff for failures
- Rate limiting compliance
- Progress tracking for long-running jobs
**DoD:** Scraper handles failures gracefully and respects site limits

#### T22 - Batch Processing Queue
**Priority:** P1 | **Estimate:** 6 hours
- Async task processing for embeddings
- Job status tracking and retry logic
- Resource optimization for batch operations
**DoD:** Large volumes of content process efficiently without blocking

---

### EPIC 3: LLM-Powered Intelligence (Light)
**Target: July 15, 2025 (Feature Freeze)**

#### T30 - Speech Summarization
**Priority:** P1 | **Estimate:** 6 hours
- One-sentence summary generation per speech
- Cached summaries in database column
- Fallback to truncated text if API fails
**DoD:** Each speech displays meaningful summary in UI

#### T31 - Topic Tag Extraction
**Priority:** P2 | **Estimate:** 6 hours
- Extract 3 key topics per speech using LLM
- Predefined tag categories for consistency
- Tag-based filtering in search interface
**DoD:** Speeches are tagged with relevant topics, searchable by tags

#### T32 - Intelligence Features in UI
**Priority:** P2 | **Estimate:** 4 hours
- Display summaries and tags in search results
- Tag-based filtering interface
- Topic trend visualization (basic)
**DoD:** Users can discover content through AI-generated insights

---

### EPIC 4: Production Readiness & Launch
**Target: July 22, 2025**

#### T40 - End-to-End Testing
**Priority:** P0 | **Estimate:** 8 hours
- Cypress E2E tests for critical user journeys
- API integration tests
- Database migration testing
- Performance benchmarking
**DoD:** Complete user workflows tested and performing within requirements

#### T41 - Security & Access Controls
**Priority:** P0 | **Estimate:** 6 hours
- Rate limiting (5 req/s for unauthenticated users)
- Input validation and sanitization
- CORS configuration for production domains
- Basic DDoS protection
**DoD:** System protected against common security vulnerabilities

#### T42 - PWA Features & Polish
**Priority:** P1 | **Estimate:** 6 hours
- PWA manifest and service worker
- Responsive design refinements
- Accessibility compliance (WCAG 2.1 AA)
- Favicon and branding
**DoD:** App installable as PWA, passes accessibility audit

#### T43 - Observability & Monitoring
**Priority:** P0 | **Estimate:** 4 hours
- Cloud Logging structured logs
- Basic uptime monitoring
- Error tracking and alerting
- Performance metrics dashboard
**DoD:** System health is visible and alerting is configured

---

## Architecture Migration Strategy

### Phase 1 (MVP): Embedded Vector Operations
```python
# api-gateway/vector_service.py
class VectorService:
    """Embedded vector operations with clear interface for future extraction"""
    
    async def generate_embedding(self, text: str) -> List[float]:
        # OpenAI API call
        
    async def similarity_search(self, query_vector: List[float], limit: int) -> List[SearchResult]:
        # pgvector query
```

### Phase 2 (Post-MVP): Service Extraction
```python
# New vector-store service
class VectorStoreService:
    """Dedicated service extracted from API gateway"""
    # Same interface, different deployment
```

### Benefits of This Approach:
1. **MVP Speed**: No inter-service complexity initially
2. **Clear Boundaries**: Vector operations isolated in separate module
3. **Easy Migration**: Extract module to new service when ready
4. **Performance**: No network overhead during MVP phase

## Definition of Done (All Tickets)

1. **Code Quality:**
   - Unit tests with >80% coverage
   - Type hints for all functions
   - Linting passes (ruff, mypy)

2. **Integration:**
   - Works in local Docker environment
   - Deployed to staging environment
   - API documentation updated

3. **Validation:**
   - Manual testing completed
   - Performance meets requirements
   - Accessibility checked (for frontend)

## Risk Mitigation Checklist

- [ ] **Integration Risk**: Use vertical slices, test continuously
- [ ] **Scraping Risk**: Test with static samples, handle site changes gracefully
- [ ] **Deployment Risk**: Deploy daily to staging, infrastructure as code
- [ ] **Performance Risk**: Load test with realistic data volumes
- [ ] **Scope Risk**: Feature freeze July 15, one week buffer for polish

## Post-MVP Backlog (Future Sprints)

### Immediate (August 2025)
- **T50**: Extract vector operations to dedicated service
- **T51**: Advanced LLM analysis (multi-document QA)
- **T52**: User accounts and personalized recommendations

### Medium-term (September 2025)
- **T60**: Real-time speech processing pipeline
- **T61**: Advanced analytics dashboard
- **T62**: Mobile app (React Native)

### Long-term (October+ 2025)
- **T70**: AI-powered policy impact analysis
- **T71**: Multi-language support
- **T72**: Public API for third-party developers

---

**Total Estimated Hours:** ~140 hours (achievable in 3 weeks with focused effort)
**Critical Path:** EPIC 0 → EPIC 1 → EPIC 4
**Parallel Development:** EPIC 2 and EPIC 3 can overlap with EPIC 1

*Last Updated: July 1, 2025*