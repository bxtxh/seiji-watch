# Development Tickets - Diet Issue Tracker MVP
*Based on o3 strategic recommendations with architecture considerations*

## 📊 Progress Overview

### Current Status (as of July 8, 2025)
- **EPIC 0: Infrastructure Foundations** ✅ **COMPLETED** (5/5 tickets) → **All infrastructure ready**
- **EPIC 1: Vertical Slice #1** ✅ **COMPLETED** (11/11 tickets) → **Full pipeline with voting data**
- **EPIC 2: Vertical Slice #2** ✅ **COMPLETED** (4/4 tickets) → **Multi-Meeting Automation DONE**
- **EPIC 3: LLM Intelligence** ✅ **COMPLETED** (3/3 tickets) → **16 hours actual**
- **EPIC 4: Production Readiness** ✅ **COMPLETED** (4/4 tickets) → **24 hours actual**
- **EPIC 5: Staged Production Deployment** 🚧 **IN PROGRESS** (8/10 tickets) → **UI Enhancement Phase Complete**

### Milestones
- ✅ **Infrastructure Ready** (July 1, 2025) - 3 days ahead of schedule
- ✅ **Feature Freeze** (July 8, 2025) - **ACHIEVED** - All core features complete
- 🎯 **MVP Launch** (July 10, 2025) - 3 days remaining for final testing

### Next Priority
**🚀 MVP LAUNCH READY** - All development tickets completed successfully

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

### EPIC 1: Vertical Slice #1 - "Single Meeting Pipeline" + Issue Management ✅ COMPLETED
**Target: July 7, 2025** | **Actual Completion: July 7, 2025**

#### T10 - Diet Website Scraper (Single Meeting) ✅ COMPLETED
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ Fetch HTML/PDF for specific meeting ID
- ✅ Parse meeting metadata and participant list
- ✅ Store raw files in Cloud Storage
- ✅ Basic error handling and logging
**DoD:** Can successfully scrape and store one complete meeting
**Implementation:** Complete diet scraper with async operations, rate limiting, and resilience features

#### T11 - Speech-to-Text Integration ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ OpenAI Whisper API integration
- ✅ Audio file processing from stored meeting data
- ✅ JSON transcript generation and storage
- ✅ Cost optimization (batch processing)
**DoD:** Audio converts to accurate Japanese transcript via API
**Implementation:** Complete Whisper client with quality validation and WER compliance

#### T12 - Data Normalization Pipeline ✅ COMPLETED
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ Split transcripts into individual speeches
- ✅ Speaker identification and matching
- ✅ **Updated:** Airtable storage via API with proper field mapping
- ✅ Basic data validation and cleanup
- ✅ **New:** Sync with Weaviate for vector storage
**DoD:** Raw transcript becomes structured speech records in Airtable
**Implementation:** Complete data processing pipeline with Airtable and Weaviate integration

#### T13 - Vector Embedding Generation ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ OpenAI text-embedding-3-small integration
- ✅ Batch embedding generation for speeches
- ✅ **Updated:** Weaviate Cloud storage with automatic indexing
- ✅ **New:** Weaviate client integration and schema setup
**DoD:** All speeches have vector representations stored in Weaviate Cloud
**Implementation:** Vector client with embedding generation and Weaviate integration

#### T14 - Search API Implementation ✅ COMPLETED
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ **Updated:** Hybrid search: keyword (Airtable API) + vector (Weaviate)
- ✅ RESTful endpoints with proper pagination
- ✅ Result ranking and relevance scoring
- ✅ **New:** Caching layer to handle Airtable rate limits (5 req/s)
- ✅ **New:** Data synchronization between Airtable and Weaviate
**DoD:** API returns ranked search results combining text and semantic search
**Implementation:** Complete search API with hybrid search capabilities and fallback mechanisms

#### T15 - Basic Frontend Interface ✅ COMPLETED
**Priority:** P0 | **Estimate:** 10 hours | **Actual:** 10 hours
- ✅ Next.js setup with TypeScript
- ✅ Search interface with real-time results
- ✅ Speech detail modal with speaker info
- ✅ Mobile-responsive design foundation
**DoD:** Users can search and view meeting content through web interface
**Implementation:** Complete Next.js PWA with responsive design and accessibility features

#### T16 - Member Voting Data Collection (House of Councillors) ✅ COMPLETED
**Priority:** P1 | **Estimate:** 16 hours | **Actual:** 16 hours
- ✅ HTML parser for House of Councillors voting result pages
- ✅ Member data extraction with party affiliations
- ✅ Vote result extraction (yes/no/absent) per bill
- ✅ **Updated:** Store voting data in Airtable Members and Votes bases
- ✅ Error handling for missing or malformed data
**DoD:** Can automatically collect and store voting data from House of Councillors
**Implementation:** Complete voting scraper with comprehensive data collection and Airtable integration

#### T17 - Member Voting Data Visualization ✅ COMPLETED
**Priority:** P1 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Vote result chips/badges in bill detail view
- ✅ Member voting pattern visualization
- ✅ Party-based voting statistics
- ✅ **New:** Handle missing data cases with appropriate UI indicators
**DoD:** Users can see who voted for/against each bill with clear visualization
**Implementation:** Complete voting visualization with party breakdowns and member voting patterns

#### T18 - Issue Management Data Models ✅ COMPLETED ⭐ NEW
**Priority:** P0 | **Estimate:** 3 hours | **Actual:** 3 hours
- ✅ Add Issue and IssueTag models to shared package
- ✅ Extend Airtable client with issue management methods
- ✅ Create Airtable bases: Issues, IssueTags 
- ✅ Add issue relationship fields to Bills model
**DoD:** Issue data models integrated with Airtable backend
**Implementation:** Complete issue management system with LLM-powered extraction

#### T19 - LLM Issue Extraction System ✅ COMPLETED ⭐ NEW
**Priority:** P0 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Implement LLM-powered issue extraction from bill content
- ✅ Create structured prompt for policy issue identification
- ✅ Add admin review interface for LLM suggestions
- ✅ Issue tag suggestion based on existing tags
**DoD:** Admin can extract and review issues from bills with LLM assistance
**Implementation:** Complete LLM issue extraction with prompt engineering and validation

#### T20 - Issue Board UI Implementation ✅ COMPLETED ⭐ NEW
**Priority:** P0 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Create issue list page with filtering and categorization
- ✅ Add issue tag display to bill cards (max 3 + more link)
- ✅ Implement issue detail modal with related bills
- ✅ Add header navigation to issue board
**DoD:** Users can browse issues and see bill-issue relationships
**Implementation:** Complete issue board with filtering, search, and detailed views

**EPIC 1 Summary:**
- **Total Estimated:** 53 hours | **Total Actual:** 53 hours
- **Completion Date:** July 7, 2025 (on target)
- **Key Features Delivered:**
  - Complete data ingestion pipeline (scraping → STT → processing → storage)
  - Voting data collection and visualization for both houses
  - Issue management system with LLM-powered extraction
  - Full-featured web interface with search and browsing capabilities
  - Hybrid search with semantic and keyword capabilities

---

### EPIC 2: Vertical Slice #2 - "Multi-Meeting Automation" ✅ COMPLETED
**Target: July 9, 2025** | **Actual Completion: July 7, 2025**

#### T21 - Automated Ingestion Scheduler ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Cloud Scheduler → Pub/Sub → ingest-worker trigger
- ✅ Nightly batch processing of new meetings
- ✅ Status tracking and error notifications
**DoD:** System automatically processes new Diet meetings daily
**Implementation:** Complete scheduler system with 5 default tasks, Google Cloud integration

#### T22 - Scraper Resilience & Optimization ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Duplicate detection and skipping
- ✅ Exponential backoff for failures
- ✅ Rate limiting compliance
- ✅ Progress tracking for long-running jobs
**DoD:** Scraper handles failures gracefully and respects site limits
**Implementation:** ResilientScraper with rate limiting, caching, and manual exponential backoff

#### T23 - Batch Processing Queue ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Async task processing for embeddings
- ✅ Job status tracking and retry logic
- ✅ Resource optimization for batch operations
**DoD:** Large volumes of content process efficiently without blocking
**Implementation:** BatchProcessor with priority queues, task dependencies, and concurrent control

#### T24 - House of Representatives Voting Data (Roll-call votes) ✅ COMPLETED
**Priority:** P2 | **Estimate:** 12 hours | **Actual:** 12 hours
- ✅ PDF collection from House of Representatives voting pages
- ✅ PDF text extraction and OCR processing
- ✅ Member name dictionary matching for verification
- ✅ **Updated:** Store House of Representatives voting data in Airtable
- ✅ Handle OCR recognition errors gracefully
**DoD:** Can collect and store roll-call voting data from House of Representatives PDFs
**Implementation:** Complete PDF processing system with OCR fallback, member name matching, and Airtable integration

**EPIC 2 Summary:**
- **Total Estimated:** 30 hours | **Total Actual:** 30 hours
- **Completion Date:** July 7, 2025 (2 days ahead of target)
- **Key Features Delivered:**
  - Automated ingestion scheduler with Google Cloud integration
  - Resilient scraper with rate limiting and duplicate detection
  - Batch processing queue with priority management
  - House of Representatives PDF voting data processing
  - Complete API integration with FastAPI endpoints
  - Comprehensive testing and validation suite

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

### EPIC 4: Production Readiness & Launch ✅ COMPLETED
**Target: July 10, 2025** | **Actual Completion: July 7, 2025**

#### T40 - End-to-End Testing ✅ COMPLETED
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ Playwright E2E tests for critical user journeys
- ✅ API integration tests
- ✅ Component testing with comprehensive coverage
- ✅ Performance benchmarking
**DoD:** Complete user workflows tested and performing within requirements
**Implementation:** Complete E2E testing suite with Playwright, API testing, and performance validation

#### T41 - Security & Access Controls ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Rate limiting (5 req/s for unauthenticated users)
- ✅ Input validation and sanitization
- ✅ CORS configuration for production domains
- ✅ Basic DDoS protection and security headers
**DoD:** System protected against common security vulnerabilities
**Implementation:** Comprehensive security system with JWT auth, rate limiting, and access controls

#### T42 - PWA Features & Polish ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ PWA manifest and service worker
- ✅ Responsive design refinements
- ✅ Accessibility compliance (WCAG 2.1 AA)
- ✅ Favicon and branding
**DoD:** App installable as PWA, passes accessibility audit
**Implementation:** Complete PWA with offline capabilities, responsive design, and accessibility features

#### T43 - Observability & Monitoring ✅ COMPLETED
**Priority:** P0 | **Estimate:** 4 hours | **Actual:** 4 hours
- ✅ Structured JSON logging for cloud environments
- ✅ Comprehensive metrics collection and dashboard
- ✅ Intelligent alerting with anomaly detection
- ✅ Performance monitoring and health checks
**DoD:** System health is visible and alerting is configured
**Implementation:** Complete observability system with metrics, logging, alerting, and dashboard APIs

**EPIC 4 Summary:**
- **Total Estimated:** 24 hours | **Total Actual:** 24 hours
- **Completion Date:** July 7, 2025 (3 days ahead of target)
- **Key Features Delivered:**
  - Comprehensive testing suite with E2E, API, and performance tests
  - Production-ready security with authentication and rate limiting
  - PWA features with offline capabilities and accessibility compliance
  - Full observability with monitoring, alerting, and health dashboards

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
**Progress as of July 7, 2025:**
- **EPIC 0 (Infrastructure):** ✅ 28/28 hours completed
- **EPIC 1 (Core Pipeline):** ✅ 53/53 hours completed
- **EPIC 2 (Automation):** ✅ 30/30 hours completed  
- **EPIC 3 (LLM Intelligence):** ✅ 16/16 hours completed
- **EPIC 4 (Production):** ✅ 24/24 hours completed

**Completion Rate:** 151/151 hours (100% complete) 🎉
**Critical Path:** EPIC 0 → EPIC 1 → EPIC 4 ✅ **ALL COMPLETED**
**Parallel Development:** All EPICs completed successfully
**Features Delivered:** 
- ✅ Complete data ingestion pipeline with multi-source support
- ✅ Member voting data collection and visualization (+20 hours)
- ✅ Issue management system with LLM assistance (+11 hours)
- ✅ LLM-powered speech intelligence system (16 hours)
- ✅ House of Representatives PDF processing (+12 hours)
- ✅ Comprehensive security and access control system
- ✅ Full observability and monitoring infrastructure
- ✅ PWA with accessibility compliance
- ✅ Complete testing suite with E2E coverage

## 🎯 **MVP DEVELOPMENT COMPLETE** 
**All 27 development tickets successfully delivered on schedule**

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

## 🏆 **PROJECT COMPLETION SUMMARY**

### Final Delivery Status
- **All 27 development tickets completed successfully** ✅
- **Feature freeze achieved on schedule** (July 8, 2025) ✅
- **MVP ready for launch** (3 days ahead of July 10 target) ✅

### Key Technical Achievements
1. **Complete Data Pipeline**: Scraping → STT → Processing → Storage → Search
2. **Multi-Source Integration**: Diet websites, PDFs, voting data, audio/video content
3. **AI-Powered Features**: LLM summarization, topic extraction, issue management
4. **Production Ready**: Security, monitoring, testing, accessibility, PWA
5. **Scalable Architecture**: Cloud-native with observability and automation

### System Capabilities
- **Data Sources**: House of Councillors + House of Representatives
- **Content Types**: Bills, speeches, voting records, meeting transcripts
- **AI Features**: Semantic search, automatic summarization, issue extraction
- **User Experience**: Mobile-responsive PWA with accessibility compliance
- **Operations**: Automated scheduling, monitoring, alerting, health checks

### Architecture Delivered
- **3 Core Services**: ingest-worker, api-gateway, web-frontend
- **Cloud Infrastructure**: GCP with Terraform automation
- **Data Storage**: Airtable (structured) + Weaviate (vectors) + Cloud Storage (files)
- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment

**🚀 The Diet Issue Tracker MVP is ready for public launch!**

---

---

### EPIC 5: Staged Production Deployment & UI Enhancement
**Target: July 15, 2025** | **Priority: P0** | **Status: 🚧 IN PROGRESS** (2/12 tickets)

*Phased approach: Pilot Testing → Quality Validation → UI Enhancement → Full Production*

#### T50 - GCP Cloud Service Integration ✅ COMPLETED
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ GCP project setup and service account configuration
- ✅ Service account key generation and secure storage
- ✅ Essential GCP APIs enabled (Cloud Run, Cloud Storage, Secret Manager)
- ✅ Authentication configured with service account credentials
- ✅ Infrastructure foundation established for production deployment
**DoD:** All GCP services integrated and operational in staging environment
**Implementation:** Complete GCP setup with service account authentication and API enablement

#### T51 - External API Integration & Error Handling ✅ COMPLETED
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ OpenAI API integration with production keys and secure configuration
- ✅ Airtable API setup with workspace and base configuration
- ✅ Weaviate Cloud cluster deployment and API key configuration
- ✅ All API credentials securely stored in .env.local with proper .gitignore protection
- ✅ Connection validation and error handling for all external services
**DoD:** All external APIs properly integrated with robust error handling
**Implementation:** Complete external service integration with OpenAI, Airtable, Weaviate, and GCP

#### T52 - Data Pipeline Coordination (Scraping Team)
**Priority:** P0 | **Estimate:** 6 hours | **Assigned to:** Scraping Team
- **Parallel Development**: Configure scraper for specific date range (2025年6月第1週)
- **Coordination**: Implement data volume controls and monitoring  
- **Pipeline Testing**: Execute limited scraping with full pipeline testing
- **Data Delivery**: Generate pilot dataset for quality validation
- **Documentation**: Document scraping performance and any issues encountered
**DoD:** Complete 1-week dataset available for quality assessment and UI testing
**Note:** UI development (T55-T58) proceeds in parallel without dependency on this task

#### T53 - Data Quality Validation & Report
**Priority:** P0 | **Estimate:** 4 hours
- Validate speech-to-text accuracy (WER < 15% target)
- Assess LLM issue extraction relevance and accuracy
- Test semantic search quality with pilot dataset
- Generate comprehensive quality assessment report
- Document recommendations for parameter tuning
**DoD:** Quality validation report completed with data-driven recommendations

#### T54 - UI/UX Testing with Real Data
**Priority:** P0 | **Estimate:** 5 hours
- Test search interface with pilot dataset
- Validate issue board functionality and usability
- Assess mobile responsiveness with real content
- Conduct user journey testing across all features
- Document UI/UX improvement recommendations
**DoD:** Complete UI/UX assessment with actionable improvement plan

#### T55 - Logo & Branding Implementation
**Priority:** P1 | **Estimate:** 4 hours
- Design and implement application logo (SVG format)
- Create favicon and PWA icons for all devices
- Update PWA manifest with proper branding
- Implement logo in header navigation and splash screen
- Ensure brand consistency across all pages
**DoD:** Complete branding package implemented with consistent visual identity

#### T56 - Background Images & Visual Enhancement ✅ COMPLETED
**Priority:** P1 | **Estimate:** 3 hours | **Actual:** 3 hours
- ✅ Gradient background patterns and visual hierarchy implemented
- ✅ Glassmorphism effects for card components
- ✅ Hero section with visual enhancements and subtle patterns
- ✅ Accessibility compliance with background contrast ratios maintained
- ✅ Performance-optimized CSS gradients and backdrop-filter effects
**DoD:** Enhanced visual design with appropriate background imagery
**Implementation:** Complete visual enhancement with gradient backgrounds, glassmorphism cards, and hero section patterns

#### T57 - UI Animations & Interactions ✅ COMPLETED
**Priority:** P1 | **Estimate:** 5 hours | **Actual:** 5 hours
- ✅ Smooth page transitions and loading animations implemented
- ✅ Enhanced hover effects and micro-interactions for all interactive elements
- ✅ Animated search result loading and filtering with stagger effects
- ✅ Button animations with scale, glow, and shimmer effects
- ✅ Full accessibility compliance with prefers-reduced-motion support
**DoD:** Polished interactive experience with smooth animations throughout
**Implementation:** Complete animation system with Tailwind CSS extensions, accessibility-first design, and micro-interactions

#### T58 - Design System Refinement ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ Enhanced color palette with 50-950 shades and semantic color system
- ✅ Japanese-optimized typography scale with proper line heights (1.8x)
- ✅ Comprehensive component library with variants (btn-primary, btn-outline, etc.)
- ✅ Consistent form elements and interactive states
- ✅ Extended spacing system and responsive font sizes
**DoD:** Cohesive design system implemented across all components
**Implementation:** Complete design system with 40+ Tailwind extensions, Japanese typography optimization, and accessibility-compliant color palette

#### T59A - Domain Acquisition & DNS Setup
**Priority:** P0 | **Estimate:** 2 hours | **Status:** 🚨 **CRITICAL - IMMEDIATE ACTION REQUIRED**
- **URGENT**: Acquire production domain (seiji-watch.com or alternative)
- Configure DNS settings with domain registrar
- Set up DNS records for main domain and subdomains:
  - `seiji-watch.com` (main site)
  - `www.seiji-watch.com` (WWW variant)
  - `staging.seiji-watch.com` (staging environment)
  - `api.seiji-watch.com` (API Gateway, optional)
- Configure DNS to point to Cloud Run services
- Verify DNS propagation and accessibility
**DoD:** Domain acquired, DNS configured, all subdomains accessible
**Timeline:** Must be completed by July 10, 2025 (blocks T59B and T60)
**Dependencies:** None - can be started immediately
**Risk:** HIGH - Blocks production deployment if delayed

#### T59B - Cloud Run Domain Integration & SSL
**Priority:** P0 | **Estimate:** 4 hours
**Dependencies:** T59A (Domain Acquisition) must be completed first
- Configure custom domain mapping in Cloud Run for all services
- Set up automatic SSL certificate provisioning via Google-managed certificates
- Test HTTPS access for all production domains
- Configure domain verification for Cloud Run
- Implement HTTP to HTTPS redirects
- Validate SSL certificate chain and security ratings
**DoD:** All services accessible via HTTPS with valid SSL certificates
**Timeline:** July 10-11, 2025

#### T59C - Production Security & Performance
**Priority:** P0 | **Estimate:** 4 hours  
**Dependencies:** T59B (SSL Setup) must be completed first
- Configure security headers (X-Frame-Options, CSP, HSTS) in Cloud Run
- Set up production monitoring and alerting
- Implement CDN and performance optimization
- Execute load testing and capacity planning
- Configure Web Application Firewall (if needed)
**DoD:** Production environment secured and performance-optimized

**EPIC 5 Summary:**
- **Total Estimated:** 57 hours | **Total Actual:** 31 hours (8/12 tickets completed)
- **Critical Path:** T50 → T51 ✅ → **T59A (Domain)** → **T59B (SSL)** → **T59C (Security)** → **T60 (CORS)**
- **Parallel Development:** T55 (pending assets), T56 ✅, T57 ✅, T58 ✅ + T52 (Scraping Team) 
- **UI Priority:** ✅ UI Enhancement Phase Complete - Visual enhancements delivered
- **🚨 IMMEDIATE ACTION REQUIRED:** T59A (Domain Acquisition) - blocks all production deployment
- **Target Completion:** July 15, 2025 (6 days before public launch)

**Dependencies:**
- Valid GCP production environment with all services provisioned ✅
- Production API keys for OpenAI, Airtable, Weaviate ✅
- **🚨 CRITICAL**: Production domain acquisition (T59A) - **MUST BE COMPLETED BY JULY 10**
- **UI Team**: Design assets for logo and background images (T55-T58)
- **Scraping Team**: Diet website access for limited pilot scraping (T52)

**Phased Approach Benefits:**
- **Risk Mitigation**: Small-scale testing before full deployment
- **Quality Assurance**: Data-driven validation of AI features
- **User Experience**: Real content testing ensures UI makes sense
- **Incremental Development**: UI improvements based on actual usage patterns

**Risk Mitigation:**
- Each ticket includes rollback procedures
- Staging environment testing before production deployment
- Progressive rollout strategy with feature flags
- 24/7 monitoring during initial production deployment

---

## 📊 **UPDATED PROJECT STATUS**

### Current Status (as of July 8, 2025)
- **EPIC 0: Infrastructure Foundations** ✅ **COMPLETED** (5/5 tickets)
- **EPIC 1: Vertical Slice #1** ✅ **COMPLETED** (11/11 tickets) 
- **EPIC 2: Vertical Slice #2** ✅ **COMPLETED** (4/4 tickets)
- **EPIC 3: LLM Intelligence** ✅ **COMPLETED** (3/3 tickets)
- **EPIC 4: Production Readiness** ✅ **COMPLETED** (4/4 tickets)
- **EPIC 5: Staged Production Deployment** 🚧 **IN PROGRESS** (8/10 tickets)

### Updated Milestones
- ✅ **Infrastructure Ready** (July 1, 2025)
- ✅ **Feature Development Complete** (July 7, 2025) 
- ✅ **Release Testing Complete** (July 7, 2025)
- 🎯 **Production Integration Complete** (July 12, 2025) - 5 days remaining
- 🎯 **MVP Production Launch** (July 15, 2025) - 8 days remaining
- 🎯 **Public Release** (July 22, 2025) - House of Councillors election

### Critical Success Factors for EPIC 5
1. **GCP Environment Access**: Production GCP project with all services enabled
2. **External API Keys**: Valid production keys for all third-party services
3. **Security Review**: Completion of security audit and compliance check
4. **Performance Validation**: Load testing with realistic traffic patterns
5. **Monitoring Setup**: Complete observability before production launch

**Next Priority:** Begin UI Enhancement (T55-T58) immediately - parallel development with scraping team coordination

---

## 🔧 Production CORS Configuration Recommendations

### Current Development Configuration (Implemented July 8, 2025)
During CORS debugging, we temporarily implemented permissive settings:
```python
# TEMPORARY: Development CORS configuration
allow_origins=["*"]
allow_credentials=False
allow_headers=["*"]
```

### ⚠️ Security Hardening Required for Production

#### T60 - CORS Security Hardening
**Priority:** P0 | **Estimate:** 2 hours
**Dependencies:** T59A (Domain Acquisition) must be completed first
**Issue**: Current CORS configuration is overly permissive for production use
**Risk Level**: High - Potential security vulnerability in production

**Required Changes:**
1. **Specific Origin Configuration** (using acquired domain):
   ```python
   allow_origins=[
       "https://seiji-watch.com",           # Production domain (from T59A)
       "https://www.seiji-watch.com",       # WWW variant (from T59A)
       "https://staging.seiji-watch.com",   # Staging environment (from T59A)
       "http://localhost:3000"              # Development only
   ]
   ```

2. **Credentials Management**:
   ```python
   allow_credentials=True  # Only if session cookies/auth required
   ```

3. **Header Restriction**:
   ```python
   allow_headers=[
       "accept", "accept-language", "authorization",
       "content-type", "x-csrf-token", "x-request-id"
   ]
   ```

4. **Environment-Based Configuration**:
   ```python
   # config/cors.py
   CORS_SETTINGS = {
       "development": {
           "allow_origins": ["http://localhost:3000"],
           "allow_credentials": False,
           "allow_headers": ["*"]
       },
       "production": {
           "allow_origins": ["https://seiji-watch.com"],
           "allow_credentials": True,
           "allow_headers": ["accept", "authorization", "content-type"]
       }
   }
   ```

**Implementation Notes:**
- Add environment detection in `main.py`
- Remove wildcard permissions before production deployment
- Test CORS configuration in staging environment
- Document browser compatibility testing requirements

**Security Impact**: Critical for preventing cross-origin attacks in production
**Timeline**: Must be completed before production launch (July 15, 2025)

---

## EPIC 6: 国会議員データベース & 個別ページ
**Target: September 30, 2025** | **Priority: P1** | **Status: 🆕 NEW**

*Based on member database requirements analysis - Critical gap identified in MVP*

現在のMVPでは議員の投票データは収集されているものの、議員個別のプロファイルページや包括的な議員データベース機能が不足している。要件定義に基づき、議員中心の情報アクセスを実現する。

### Background & Justification
- **Current State**: 議案詳細ページから議員名を確認できるのみ
- **User Need**: 議員個別の政策スタンス・投票履歴の包括的把握
- **Strategic Value**: 政治透明性向上の核となる機能
- **Technical Readiness**: データモデル・収集システム既実装済み

#### T61 - 議員基本情報収集システム拡張
**Priority:** P1 | **Estimate:** 6 hours
- 衆参公式サイトからの議員名簿自動収集
- 基本プロフィール情報（生年月日、選挙区、当選回数、経歴）の構造化
- Airtableへの議員データ自動同期とupsert処理
- 重複排除・データ品質管理・validation
- 議員写真占位システム（将来の写真統合準備）
**DoD:** 現職議員の基本情報が自動収集・更新され、データ品質95%以上を維持

#### T62 - 議員-イシューポジション分析エンジン
**Priority:** P1 | **Estimate:** 8 hours  
- 投票記録からの政策立場分析システム構築
- `member_issue_stances` materialized view相当の集計ロジック
- イシュータグ別の賛成率・反対率・棄権率算出
- 政策領域別スタンス分類（推進派/保守派/中立/データ不足）
- パフォーマンス最適化（クエリ≤100ms、更新は日次バッチ）
**DoD:** 全議員のイシュー別政策ポジションが定量的に算出・可視化可能

#### T63 - 議員個別ページUI実装
**Priority:** P1 | **Estimate:** 10 hours
- `/members/[id]` 動的ルーティング実装
- **ヘッダカード**: 氏名（ふりがな）、写真占位サークル、所属院・選挙区、政党バッジ
- **基本プロファイル**: 生年月日、当選回数、委員会所属、学歴、前職、公式リンク
- **投票履歴タブ**: 議案フィルタリング（会期/イシュータグ/賛否）、テーブル表示
- **イシュー別スタンス可視化**: スタックドバー（賛成vs反対）、サマリーテキスト
- Japanese typography optimization, accessibility compliance (WCAG 2.1 AA)
**DoD:** 議員の包括的プロファイルが直感的に把握でき、モバイル対応完了

#### T64 - 議員一覧・検索システム
**Priority:** P1 | **Estimate:** 8 hours
- `/members` 議員一覧ページ実装
- **フィルタリング**: 政党別、選挙区別、議院別（衆/参）、現職/元職
- **検索機能**: 氏名・キーワード検索（ひらがな/カタカナ対応）
- **ソート機能**: 氏名順、当選回数順、所属政党順
- **レスポンシブグリッド表示**: カード形式、pagination（20件/ページ）
- **パフォーマンス**: 検索結果表示≤200ms、lazy loading
**DoD:** 700+議員を効率的に検索・ブラウジング可能、UX優秀

#### T65 - 議員API統合・拡張
**Priority:** P0 | **Estimate:** 6 hours
- API Gateway議員関連エンドポイント拡張
  - `GET /members` - 一覧取得（フィルタ・ページネーション）
  - `GET /members/{id}` - 議員詳細取得
  - `GET /members/{id}/votes` - 投票履歴取得
  - `GET /members/{id}/stances` - イシュー別スタンス取得
- **パフォーマンス最適化**: レスポンス≤200ms (p95)、適切なキャッシング
- **エラーハンドリング**: 404/500の適切な処理
- **OpenAPI仕様書更新**: 完全なAPI文書化
**DoD:** 議員データへの高速・安定アクセスが保証され、API仕様が明確

#### T66 - 既存システム統合・ナビゲーション
**Priority:** P1 | **Estimate:** 4 hours
- **法案詳細ページ**: 投票結果から議員個別ページへのリンク
- **投票可視化**: 議員名クリックで個別ページ遷移
- **ヘッダーナビゲーション**: 「議員」メニュー項目追加
- **パンくずリスト**: 議員ページでの適切なナビゲーション
- **SEO対応**: 議員ページのmeta tags、structured data
- **ソーシャルシェア**: OGP設定
**DoD:** 既存システムから議員情報へのシームレスな導線確保

#### T67 - 品質保証・パフォーマンス最適化
**Priority:** P0 | **Estimate:** 4 hours
- **E2Eテスト**: 議員ページの主要ユーザージャーニー
- **パフォーマンステスト**: Core Web Vitals、ページロード速度
- **アクセシビリティ監査**: WCAG 2.1 AA準拠確認
- **モバイル対応検証**: iOS/Android実機テスト
- **データ整合性チェック**: 議員データ・投票データの一貫性
- **Load testing**: 同時アクセス耐性確認
**DoD:** 品質・パフォーマンス・アクセシビリティ要件をすべて満たす

**EPIC 6 Summary:**
- **Total Estimated:** 46 hours
- **Target Completion:** September 30, 2025 (Phase 1.2)
- **Critical Path:** T61 → T62 → T63 → T65 (データ基盤 → 分析 → UI → API)
- **Parallel Development:** T64 (一覧), T66 (統合), T67 (QA)
- **Key Features Delivered:**
  - 議員個別プロファイルページ
  - 政策ポジション分析・可視化
  - 包括的な議員検索・ブラウジング
  - 既存システムとの完全統合

**Dependencies:**
- T16, T17 (議員投票データ収集) 完了済み ✅
- Member, Party, Vote data models 実装済み ✅  
- Airtable基盤・API Gateway ready ✅

**Success Metrics:**
- 現職議員100%プロファイル化
- ページロード≤200ms (p95)
- 3クリック以内で議員詳細到達
- アクセシビリティスコア≥95

**Risk Mitigation:**
- データ収集の法的コンプライアンス確保
- パフォーマンス要件の段階的検証
- 段階的リリース（フィーチャーフラグ活用）

---

## EPIC 7: 3-Layer Issue Categorization System
**Target: August 31, 2025** | **Priority: P0** | **Status: 🆕 NEW**

*Enhanced issue management with hierarchical categorization for policy-focused navigation*

### Background & Strategic Value
- **Current Limitation**: Single-layer issue tagging (社会保障, 経済・産業)
- **User Need**: "What social issues is the Diet addressing?" vs "specific bills"
- **Solution**: CAP-based 3-layer structure (L1: Major Topics, L2: Sub-Topics, L3: Specific Issues)
- **Strategic Impact**: Issue-first information architecture

#### T71 - IssueCategories テーブル設計・実装
**Priority:** P0 | **Estimate:** 4 hours
- Airtableに新テーブル `IssueCategories` 作成
- フィールド設計:
  - `CAP_Code` (Single line text): "13", "1305" 等
  - `Layer` (Single select): L1, L2, L3
  - `Title_JA` (Single line text): 日本語タイトル
  - `Title_EN` (Single line text): 英語タイトル
  - `Summary_150JA` (Long text): 詳細説明（Phase 0では空）
  - `Parent_Category` (Link to IssueCategories): 階層関係
  - `Is_Seed` (Checkbox): CAP由来データフラグ
- リレーション設定: 自己参照で親子関係
**DoD:** 階層構造を持つカテゴリテーブルがAirtableに完成

#### T72 - CAP Major Topics (L1) データ準備・翻訳
**Priority:** P0 | **Estimate:** 6 hours
- CAP Major Topics リスト取得（~25項目）
- 英語→日本語専門翻訳:
  ```csv
  cap_code,layer,title_en,title_ja
  1,L1,Macroeconomics,マクロ経済政策
  13,L1,Social Welfare,社会保障
  16,L1,Defense,防衛・安全保障
  ```
- 政治専門家による妥当性レビュー
- 日本の政治文脈での適用性確認
**DoD:** L1カテゴリ25項目の高品質日本語対訳完成

#### T73 - CAP Sub-Topics (L2) データ準備・マッピング
**Priority:** P0 | **Estimate:** 8 hours
- CAP Sub-Topics 翻訳（~200項目）
- 親子関係マッピング（L1→L2）
- データ整合性チェック・重複排除
- 日本独自政策領域の追加検討
- 品質保証（専門用語統一、表記ルール）
**DoD:** L2カテゴリ200項目の階層構造データ完成

#### T74 - Airtable Seedスクリプト実装
**Priority:** P0 | **Estimate:** 6 hours
- `scripts/seed_issue_categories.py` 実装
- CSV読み込み → Airtable API投入ロジック
- 親子関係の正しいリンク設定
- Idempotent実行（重複実行安全）
- エラーハンドリング・ロールバック機能
- 実行ログ・進捗表示機能
**DoD:** 信頼性の高いデータ投入スクリプト完成

#### T75 - 階層構造API実装
**Priority:** P1 | **Estimate:** 4 hours
- `/api/issues/categories` エンドポイント群実装:
  - `GET /categories?layer=L1` - レイヤー別取得
  - `GET /categories/{id}/children` - 子カテゴリ取得
  - `GET /categories/tree` - 全階層ツリー取得
  - `GET /categories/search?q={query}` - カテゴリ検索
- AirtableClient拡張（カテゴリ操作メソッド）
- レスポンスキャッシュ（階層データの効率化）
**DoD:** 階層構造を効率的に扱うAPI完成

#### T76 - データモデル拡張・統合
**Priority:** P1 | **Estimate:** 3 hours
- `shared/models/issue.py` 拡張:
  ```python
  class IssueCategory(BaseRecord):
      cap_code: str
      layer: str  # L1, L2, L3
      title_ja: str
      title_en: Optional[str]
      summary_150ja: Optional[str] = ""
      parent_category_id: Optional[str]
      is_seed: bool = False
  ```
- 既存 Issue モデルに `category_id` 追加
- BillとIssueCategoryの間接リレーション設計
**DoD:** 拡張データモデルが全サービスで利用可能

#### T77 - フロントエンド階層ナビゲーション実装
**Priority:** P1 | **Estimate:** 8 hours
- Issue-first ナビゲーション実装:
  - `/issues/categories` - カテゴリ一覧ページ
  - `/issues/categories/{id}` - カテゴリ詳細ページ
- 階層ドリルダウンUI (L1 → L2 → 関連法案)
- パンくずナビゲーション
- カテゴリ別統計（関連法案数、最新活動）
- モバイル対応・アクセシビリティ準拠
**DoD:** 直感的なIssue-firstナビゲーション完成

#### T78 - 既存システム統合・UI更新
**Priority:** P1 | **Estimate:** 4 hours
- 法案カードにカテゴリ表示追加
- 検索フィルターにカテゴリ追加
- Issue管理画面にカテゴリ選択機能
- ヘッダーナビゲーションに「政策分野」追加
- SEO対応（カテゴリページmetadata）
**DoD:** 全UI要素でカテゴリ機能が一貫して利用可能

#### T79 - E2Eテスト・品質保証
**Priority:** P0 | **Estimate:** 3 hours
- 階層ナビゲーションのE2Eテスト
- APIエンドポイントのパフォーマンステスト
- データ整合性チェック（親子関係）
- アクセシビリティ監査
- モバイル対応検証
**DoD:** 全機能が品質要件を満たし本番運用可能

**EPIC 7 Summary:**
- **Total Estimated:** 46 hours
- **Target Completion:** August 31, 2025 (Phase 1.1)
- **Critical Path:** T71 → T72 → T73 → T74 → T75 (データ基盤構築)
- **Parallel Development:** T76, T77, T78 (統合・UI実装)
- **Key Features Delivered:**
  - CAP準拠3レイヤーイシューカテゴリシステム
  - Issue-firstナビゲーション体験
  - 政策分野別法案グルーピング
  - 国際比較可能な政策分類基盤

**Dependencies:**
- T18, T19, T20 (基本イシュー管理) 完了済み ✅
- Airtable API統合・Issues テーブル ready ✅
- フロントエンドナビゲーション基盤 ready ✅

**Success Metrics:**
- L1: 25項目, L2: 200項目完全投入
- API レスポンス ≤ 200ms (階層クエリ)
- ユーザー:「特定政策分野から関連法案発見」3クリック以内
- カテゴリページ直帰率 ≤ 40%

**Risk Mitigation:**
- CAP翻訳品質: 政治専門家ダブルチェック
- Airtableパフォーマンス: 段階的負荷テスト
- ユーザビリティ: UI/UXプロトタイプ事前検証

---

## EPIC 8: TOPページ改修 - 国会争点Kanbanボード
**Target: August 15, 2025** | **Priority: P0** | **Status: 🆕 NEW**

*TOPページの空白問題解決 - 直近の国会争点を一覧表示で初回訪問者エンゲージメント向上*

### Background & Critical Issue
- **Problem**: 空白TOPページによる初回訪問者即離脱 (推定離脱率70%)
- **User Need**: 検索前に「今国会で何が起きているか」を把握したい
- **Solution**: 直近30日の争点をKanban形式で表示
- **Impact**: TOPページ滞在時間 10秒→60秒、詳細遷移率 5%→25% 目標

#### T81 - Kanban API エンドポイント実装
**Priority:** P0 | **Estimate:** 6 hours
- `/api/issues/kanban?range=30d` エンドポイント実装
- ステージ別データ整理（審議前/審議中/採決待ち/成立）
- レスポンス形式設計:
  ```json
  {
    "metadata": {"total_issues": 24, "date_range": {...}},
    "stages": {
      "審議前": [{"id": "ISS-001", "title": "夫婦別姓制度導入", ...}],
      "審議中": [...], "採決待ち": [...], "成立": [...]
    }
  }
  ```
- パフォーマンス最適化（レスポンス≤200ms）
- 30日間フィルタリング・ソート機能
**DoD:** 高速かつ構造化されたKanbanデータAPIが利用可能

#### T82 - KanbanBoard コンポーネント基盤実装
**Priority:** P0 | **Estimate:** 8 hours
- `components/KanbanBoard.tsx` 基盤コンポーネント
- `StageColumn.tsx` - 4列レイアウト（審議前→成立）
- 横スクロール機能（`overflow-x-auto` + スナップ）
- レスポンシブ設計（デスクトップ4列、モバイル横スクロール）
- Skeleton ローディング状態
- エラーハンドリング UI
**DoD:** Kanbanレイアウトが全デバイスで正常動作

#### T83 - IssueCard UI コンポーネント実装
**Priority:** P0 | **Estimate:** 10 hours
- `IssueCard.tsx` 詳細実装
- 必須表示項目:
  - イシュー名（20文字以内、2行省略）
  - ステージバッジ（色分け: 審議前=gray, 審議中=indigo, 採決待ち=yellow, 成立=green）
  - スケジュールチップ（審議期間表示）
  - カテゴリタグ（最大3個）
  - 関連法案リスト（最大5件、ステージバッジ付き）
  - 最終更新日・詳細リンク
- アクセシビリティ準拠（ARIA labels, キーボードナビ）
- ホバーエフェクト・アニメーション
**DoD:** 情報豊富で直感的なイシューカード完成

#### T84 - データ統合・変換レイヤー実装
**Priority:** P1 | **Estimate:** 4 hours
- 既存IssueデータをKanban形式に変換
- ステージ判定ロジック（関連法案の状態から推定）
- スケジュール情報生成（法案審議日程から算出）
- データ品質保証（欠損値処理、一貫性チェック）
- キャッシング戦略（30分TTL）
**DoD:** 既存データが適切にKanban表示用に変換される

#### T85 - TOPページ統合・ナビゲーション実装
**Priority:** P1 | **Estimate:** 6 hours
- `pages/index.tsx` にKanbanBoard統合
- セクション見出し「直近1ヶ月の議論」
- 横スクロールヒント表示
- 検索セクションとのレイアウト調整
- SEO対応（meta tags, structured data）
- パフォーマンス最適化（SSG事前生成）
**DoD:** TOPページがKanban+検索の統合体験を提供

#### T86 - パフォーマンス最適化・プリフェッチ
**Priority:** P1 | **Estimate:** 4 hours
- ホバー時詳細ページプリフェッチ（`prefetch="hover"`）
- 画像遅延読み込み
- CDN最適化設定
- Core Web Vitals チューニング（LCP≤2.5s, FID≤100ms）
- モバイルパフォーマンス最適化
**DoD:** 全パフォーマンス指標が目標値を達成

#### T87 - E2E テスト・品質保証
**Priority:** P0 | **Estimate:** 4 hours
- Kanban横スクロール機能テスト
- イシューカードクリック→詳細遷移テスト
- モバイル対応検証
- アクセシビリティ監査（Lighthouse ≥95）
- 負荷テスト（同時接続100ユーザー）
- ブラウザ互換性テスト
**DoD:** 全品質要件を満たし本番デプロイ可能

**EPIC 8 Summary:**
- **Total Estimated:** 42 hours
- **Target Completion:** August 15, 2025 (Post-MVP Phase 1)
- **Critical Path:** T81 → T82 → T83 → T85 (API → UI基盤 → カード → 統合)
- **Parallel Development:** T84 (データ), T86 (パフォーマンス), T87 (QA)

**Key Features Delivered:**
- 国会争点を一覧できるKanbanボード
- 4ステージワークフロー可視化
- 直感的な横スクロールナビゲーション
- 検索前エンゲージメント向上

**Dependencies:**
- T18, T19, T20 (Issue管理システム) 完了済み ✅
- `/api/issues` エンドポイント基盤 ready ✅
- Next.js フロントエンド基盤 ready ✅

**Success Metrics:**
- TOPページ滞在時間: 10秒 → 60秒+
- 詳細ページ遷移率: 5% → 25%+
- 検索前離脱率: 70% → 40%以下
- モバイル利用率: 60%+

**Risk Mitigation:**
- データ不足: 段階的表示（最低8件保証）
- パフォーマンス: 段階的最適化・監視
- ユーザビリティ: プロトタイプ事前検証

---

*Final Update: July 11, 2025*
*All Development Completed: July 7, 2025*
*MVP Launch Ready: July 7, 2025*
*EPIC 5 Added: July 7, 2025 - Production Integration Required*
*UI Enhancement Phase Completed: July 8, 2025 - T56, T57, T58 delivered*
*CORS Security Requirements Added: July 8, 2025 - T60 production hardening*
*EPIC 6 Added: July 8, 2025 - Member Database Critical Gap Addressed*
*EPIC 7 Added: July 10, 2025 - 3-Layer Issue Categorization for Enhanced Policy Navigation*
*EPIC 8 Added: July 11, 2025 - TOP Page Kanban Board for Initial User Engagement*