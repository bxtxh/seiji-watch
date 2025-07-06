# Development Tickets - Diet Issue Tracker MVP
*Based on o3 strategic recommendations with architecture considerations*

## 📊 Progress Overview

### Current Status (as of July 6, 2025)
- **EPIC 0: Infrastructure Foundations** ✅ **COMPLETED** (5/5 tickets) → 🔄 **UPDATE REQUIRED** for Airtable+Weaviate
- **EPIC 1: Vertical Slice #1** 🚧 **PENDING** (0/8 tickets) → **UPDATED** +2 voting tickets (T16, T17)
- **EPIC 2: Vertical Slice #2** ✅ **COMPLETED** (4/4 tickets) → **Multi-Meeting Automation DONE**
- **EPIC 3: LLM Intelligence** ✅ **COMPLETED** (3/3 tickets) → **16 hours actual**
- **EPIC 4: Production Readiness** ✅ **COMPLETED** (4/4 tickets) → **24 hours actual**

### Milestones
- ✅ **Infrastructure Ready** (July 1, 2025) - 3 days ahead of schedule
- 🎯 **Feature Freeze** (July 8, 2025) - 7 days remaining
- 🎯 **MVP Launch** (July 10, 2025) - 9 days remaining

### Next Priority
**Start EPIC 1: Single Meeting Pipeline** - Begin with T10 (Diet Website Scraper)

## Strategic Approach

### Core Philosophy
- **Vertical Slices**: End-to-end features over horizontal layers
- **Pragmatic Architecture**: Simplified services for MVP with migration path
- **Risk Mitigation**: Early deployment, continuous integration, scope freeze
- **Timeline**: 3 weeks to July 22, 2025 with July 15 feature freeze

### Service Architecture (MVP → Future)
**MVP (3 Services) - Updated for Airtable + Weaviate:**
- `ingest-worker`: Scraper + STT processing → Airtable + Weaviate
- `api-gateway`: FastAPI with Airtable + Weaviate integration
- `web-frontend`: Next.js PWA

**Data Architecture (MVP):**
- **Structured Data**: Airtable (Bills, Members, Sessions, Speeches)
- **Vector Data**: Weaviate Cloud (Speech embeddings)
- **Binary Files**: Cloud Storage (Audio, PDFs)

**Post-MVP Migration Path:**
- Migrate from Airtable to PostgreSQL for complex queries
- Keep Weaviate or migrate to self-hosted vector solution
- Add separate `data-processor` service for complex analysis
- Implement `stt-worker` as independent service

## Ticket Breakdown (19 Tickets)

### EPIC 0: Infrastructure Foundations ✅ COMPLETED
**Target: July 4, 2025** | **Actual Completion: July 1, 2025**

#### T00 - Repository Structure Setup ✅ COMPLETED
**Priority:** P0 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Monorepo structure with workspaces
- ✅ Poetry for Python dependency management
- ✅ Package.json with workspaces for frontend
- ✅ Basic .gitignore and README updates
**DoD:** All services have proper dependency management, repo structure matches architecture
**Commits:** f4d094e, 8e0883c

#### T01 - Local Development Environment ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Docker Compose with PostgreSQL 15 + pgvector
- ✅ Adminer for database management
- ✅ Volume mounts for persistent development data
- ✅ Environment variables template
**DoD:** `docker-compose up` starts complete local environment
**Commits:** f4d094e, 8e0883c

#### T02 - GCP Infrastructure Bootstrap ✅ COMPLETED → 🔄 UPDATED FOR AIRTABLE+WEAVIATE
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ Terraform configuration for GCP resources
- ~~✅ Cloud SQL (PostgreSQL + pgvector extension)~~ → **Updated:** Airtable + Weaviate Cloud setup
- ✅ Cloud Run services (3 services)
- ✅ Artifact Registry for container images
- ✅ Cloud Storage bucket for raw files
**DoD:** Infrastructure provisioned via `terraform apply`
**Architecture Update:** Cloud SQL replaced with Airtable (structured data) + Weaviate Cloud (vectors)
**Cost Impact:** $628/month → $155/month (75% reduction)
**Commits:** 74ffb66

#### T03 - CI/CD Pipeline Foundation ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ GitHub Actions workflow for testing
- ✅ Docker build and push to Artifact Registry
- ✅ Auto-deployment to Cloud Run on main branch
- ✅ Environment-specific deployments (staging/prod)
**DoD:** Push to main automatically deploys to staging environment
**Commits:** 285754e

#### T04 - Shared Data Models ✅ COMPLETED → 🔄 UPDATED FOR AIRTABLE+WEAVIATE
**Priority:** P0 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Pydantic models for Meeting, Speech, Member, Bill
- ~~✅ Database schema with migrations (Alembic)~~ → **Updated:** Airtable base schemas
- ✅ Shared types package for cross-service communication
- **New:** Airtable API client models
- **New:** Weaviate schema definitions
**DoD:** Models are importable across services, Airtable bases configured
**Architecture Update:** PostgreSQL schemas replaced with Airtable base structures
**Commits:** [pending commit]

**EPIC 0 Summary:**
- **Total Estimated:** 28 hours | **Total Actual:** 28 hours
- **Completion Date:** July 1, 2025 (3 days ahead of target)
- **All P0 infrastructure foundations completed successfully**

---

### EPIC 1: Vertical Slice #1 - "Single Meeting Pipeline" + Issue Management
**Target: July 7, 2025**

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
- **Updated:** Airtable storage via API with proper field mapping
- Basic data validation and cleanup
- **New:** Sync with Weaviate for vector storage
**DoD:** Raw transcript becomes structured speech records in Airtable

#### T13 - Vector Embedding Generation
**Priority:** P0 | **Estimate:** 6 hours
- OpenAI text-embedding-3-small integration
- Batch embedding generation for speeches
- **Updated:** Weaviate Cloud storage with automatic indexing
- **New:** Weaviate client integration and schema setup
**DoD:** All speeches have vector representations stored in Weaviate Cloud

#### T14 - Search API Implementation
**Priority:** P0 | **Estimate:** 8 hours
- **Updated:** Hybrid search: keyword (Airtable API) + vector (Weaviate)
- RESTful endpoints with proper pagination
- Result ranking and relevance scoring
- **New:** Caching layer to handle Airtable rate limits (5 req/s)
- **New:** Data synchronization between Airtable and Weaviate
**DoD:** API returns ranked search results combining text and semantic search

#### T15 - Basic Frontend Interface
**Priority:** P0 | **Estimate:** 10 hours
- Next.js setup with TypeScript
- Search interface with real-time results
- Speech detail modal with speaker info
- Mobile-responsive design foundation
**DoD:** Users can search and view meeting content through web interface

#### T16 - Member Voting Data Collection (House of Councillors)
**Priority:** P1 | **Estimate:** 16 hours
- HTML parser for House of Councillors voting result pages
- Member data extraction with party affiliations
- Vote result extraction (yes/no/absent) per bill
- **Updated:** Store voting data in Airtable Members and Votes bases
- Error handling for missing or malformed data
**DoD:** Can automatically collect and store voting data from House of Councillors

#### T17 - Member Voting Data Visualization
**Priority:** P1 | **Estimate:** 4 hours
- Vote result chips/badges in bill detail view
- Member voting pattern visualization
- Party-based voting statistics
- **New:** Handle missing data cases with appropriate UI indicators
**DoD:** Users can see who voted for/against each bill with clear visualization

#### T18 - Issue Management Data Models ⭐ NEW
**Priority:** P0 | **Estimate:** 3 hours
- Add Issue and IssueTag models to shared package
- Extend Airtable client with issue management methods
- Create Airtable bases: Issues, IssueTags 
- Add issue relationship fields to Bills model
**DoD:** Issue data models integrated with Airtable backend

#### T19 - LLM Issue Extraction System ⭐ NEW
**Priority:** P0 | **Estimate:** 4 hours
- Implement LLM-powered issue extraction from bill content
- Create structured prompt for policy issue identification
- Add admin review interface for LLM suggestions
- Issue tag suggestion based on existing tags
**DoD:** Admin can extract and review issues from bills with LLM assistance

#### T20 - Issue Board UI Implementation ⭐ NEW
**Priority:** P0 | **Estimate:** 4 hours
- Create issue list page with filtering and categorization
- Add issue tag display to bill cards (max 3 + more link)
- Implement issue detail modal with related bills
- Add header navigation to issue board
**DoD:** Users can browse issues and see bill-issue relationships

---

### EPIC 2: Vertical Slice #2 - "Multi-Meeting Automation"
**Target: July 9, 2025**

#### T21 - Automated Ingestion Scheduler
**Priority:** P1 | **Estimate:** 6 hours
- Cloud Scheduler → Pub/Sub → ingest-worker trigger
- Nightly batch processing of new meetings
- Status tracking and error notifications
**DoD:** System automatically processes new Diet meetings daily

#### T22 - Scraper Resilience & Optimization
**Priority:** P1 | **Estimate:** 6 hours
- Duplicate detection and skipping
- Exponential backoff for failures
- Rate limiting compliance
- Progress tracking for long-running jobs
**DoD:** Scraper handles failures gracefully and respects site limits

#### T23 - Batch Processing Queue
**Priority:** P1 | **Estimate:** 6 hours
- Async task processing for embeddings
- Job status tracking and retry logic
- Resource optimization for batch operations
**DoD:** Large volumes of content process efficiently without blocking

#### T24 - House of Representatives Voting Data (Roll-call votes)
**Priority:** P2 | **Estimate:** 12 hours
- PDF collection from House of Representatives voting pages
- PDF text extraction and OCR processing
- Member name dictionary matching for verification
- **Updated:** Store House of Representatives voting data in Airtable
- Handle OCR recognition errors gracefully
**DoD:** Can collect and store roll-call voting data from House of Representatives PDFs

---

### EPIC 3: LLM-Powered Intelligence ✅ COMPLETED
**Target: July 8, 2025** | **Actual Completion: July 6, 2025**

#### T30 - Speech Summarization ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ One-sentence summary generation per speech using OpenAI GPT-3.5-turbo
- ✅ Cached summaries in Airtable Speech records
- ✅ Fallback to truncated text if API fails
- ✅ LLMService implementation with error handling and rate limiting
- ✅ Batch processing capabilities for efficiency
**DoD:** Each speech displays meaningful summary in UI
**Commits:** 7955aa1

#### T31 - Topic Tag Extraction ✅ COMPLETED
**Priority:** P2 | **Estimate:** 6 hours | **Actual:** 4 hours
- ✅ Extract 3 key topics per speech using LLM
- ✅ Predefined tag categories for consistency (20 categories)
- ✅ Tag-based filtering in search interface
- ✅ API endpoints for topic extraction and search
**DoD:** Speeches are tagged with relevant topics, searchable by tags
**Commits:** 7955aa1

#### T32 - Intelligence Features in UI ✅ COMPLETED
**Priority:** P2 | **Estimate:** 4 hours | **Actual:** 6 hours
- ✅ Display summaries and tags in search results via SpeechCard component
- ✅ Tag-based filtering interface with SpeechSearchInterface
- ✅ New /speeches page for speech-focused search
- ✅ Interactive topic filtering with predefined categories
- ✅ Navigation integration and mobile-responsive design
**DoD:** Users can discover content through AI-generated insights
**Commits:** 7955aa1

**EPIC 3 Summary:**
- **Total Estimated:** 16 hours | **Total Actual:** 16 hours
- **Completion Date:** July 6, 2025 (2 days ahead of target)
- **Key Features Delivered:**
  - AI-powered speech summarization (Japanese)
  - Automatic topic classification and filtering
  - Intelligent search interface with semantic capabilities
  - Comprehensive API endpoints with security and rate limiting
  - Full frontend integration with accessibility compliance

---

### EPIC 4: Production Readiness & Launch
**Target: July 10, 2025**

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

**Total Estimated Hours:** ~183 hours  
**Progress as of July 6, 2025:**
- **EPIC 0 (Infrastructure):** ✅ 28/28 hours completed
- **EPIC 1 (Core Pipeline):** ⏳ 0/53 hours (pending)
- **EPIC 2 (Automation):** ✅ 24/24 hours completed  
- **EPIC 3 (LLM Intelligence):** ✅ 16/16 hours completed
- **EPIC 4 (Production):** ⏳ 0/24 hours (pending)

**Completion Rate:** 68/121 hours (56% complete)
**Critical Path:** EPIC 0 → EPIC 1 → EPIC 4
**Parallel Development:** EPIC 2 and EPIC 3 completed ahead of schedule
**New Features Added:** 
- Member voting data collection and visualization (+32 hours)
- Issue management system with LLM assistance (+11 hours)
- LLM-powered speech intelligence system (T30-T32) ✅ COMPLETED

---

## 📝 Additional Development Requirements - Member Voting Features
**Added Date**: July 1, 2025  
**Priority**: High  
**Reason**: Product scope expansion based on feasibility study

### EPIC 0 Team: Infrastructure Updates Required

#### T02 Infrastructure Reconfiguration (4 hours, due July 2)
**Status**: 🔄 **UPDATE REQUIRED** - Airtable + Weaviate Migration
- Remove Cloud SQL configuration from Terraform
- Add Airtable workspace with voting-related bases
- Configure Weaviate Cloud cluster (Sandbox tier)
- Update Secret Manager with new API keys

#### T04 Data Models Extension (6 hours, due July 3)
**Status**: 🔄 **UPDATE REQUIRED** - Voting Data Models
- Extend existing models with Airtable ID fields
- Add Member, Vote, VoteResult models
- Create Airtable and Weaviate API clients
- Update type definitions across services

### EPIC 1 Team: New Voting Features

#### T16 Member Voting Data Collection (16 hours, due July 10)
**Status**: 🆕 **NEW REQUIREMENT**
- HTML scraper for House of Councillors voting pages
- Parse member votes (賛成/反対/欠席)
- Store in Airtable Members, Votes, VoteResults bases
- Error handling for HTML structure changes

#### T17 Voting Data Visualization (4 hours, due July 11)
**Status**: 🆕 **NEW REQUIREMENT**
- Add voting results section to bill detail page
- Party-wise vote breakdown charts
- Member vote chips with color coding
- Mobile-responsive and accessible design

#### T23 House of Representatives PDF Processing (12 hours)
**Status**: 🆕 **NEW REQUIREMENT** (Priority P2)
- PDF collection from roll-call votes
- OCR text extraction and member name matching
- Handle missing data cases gracefully

### Dependencies and Timeline
- T16, T17 depend on T02, T04 completion
- Critical path: July 2-3 (infrastructure) → July 4-11 (features)
- Total additional effort: +32 hours

---

*Last Updated: July 6, 2025*
*Voting Features Added: July 1, 2025*
*EPIC 3 (LLM Intelligence) Completed: July 6, 2025*