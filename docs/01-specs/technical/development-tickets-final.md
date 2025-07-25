# Development Tickets - Diet Issue Tracker MVP
*Based on o3 strategic recommendations with architecture considerations*

## 📊 Progress Overview

### Current Status (as of July 15, 2025)
- **EPIC 0: Infrastructure Foundations** ✅ **COMPLETED** (5/5 tickets) → **All infrastructure ready**
- **EPIC 1: Vertical Slice #1** ✅ **COMPLETED** (11/11 tickets) → **Full pipeline with voting data**
- **EPIC 2: Vertical Slice #2** ✅ **COMPLETED** (4/4 tickets) → **Multi-Meeting Automation DONE**
- **EPIC 3: LLM Intelligence** ✅ **COMPLETED** (3/3 tickets) → **16 hours actual**
- **EPIC 4: Production Readiness** ✅ **COMPLETED** (4/4 tickets) → **24 hours actual**
- **EPIC 5: Staged Production Deployment** 🚧 **IN PROGRESS** (8/10 tickets) → **UI Enhancement Phase Complete**
- **EPIC 9: 法的コンプライアンス** ✅ **COMPLETED** (3/3 tickets) → **利用規約・プライバシーポリシー実装完了**
- **EPIC 15: Issue Notification System** ❌ **NOT IMPLEMENTED** (0/4 tickets) → **Email alerts & watch functionality PENDING**
- **EPIC 16: Bills ↔ PolicyCategory関連付けシステム** ✅ **COMPLETED** (5/5 tickets) → **Bills ↔ PolicyCategory integration fully implemented**
- **EPIC 17: フロントエンド UI 改善** ✅ **COMPLETED** (3/3 tickets) → **UI improvements based on user feedback**
- **EPIC 18: Code Quality - E501 Compliance** 🚧 **PENDING** (0/4 tickets) → **1,242 line length errors for post-MVP cleanup**
- **EPIC 19: CI/CD Lint Error Fixes** ✅ **COMPLETED** (4/4 tickets) → **All CI/CD pipeline issues resolved**
- **EPIC 20: 外部関係者共同手動テスト** 🚧 **PENDING** (5/5 tickets) → **Comprehensive external user testing before MVP launch**

### Milestones
- ✅ **Infrastructure Ready** (July 1, 2025) - 3 days ahead of schedule
- ✅ **Feature Freeze** (July 8, 2025) - **ACHIEVED** - All core features complete
- 🎯 **MVP Launch** (July 10, 2025) - 3 days remaining for final testing

### Next Priority
**✅ EPIC 16: Bills ↔ PolicyCategory関連付けシステム** - 5/5 tickets COMPLETED. Full end-to-end integration complete. Frontend successfully integrated with new API endpoints.

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

## Ticket Breakdown (22 Tickets)

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
**Priority:** P0 | **Estimate:** 2 hours | **Status:** ✅ **COMPLETED July 11, 2025**
- ✅ **COMPLETED**: Acquired production domain (`politics-watch.jp`)
- ⏳ **PENDING**: Configure DNS settings with domain registrar
- Set up DNS records for main domain:
  - `politics-watch.jp` (main site) - **DOMAIN MAPPING READY**
  - Required A records: 216.239.32.21, 216.239.34.21, 216.239.36.21, 216.239.38.21
  - Required AAAA records: 2001:4860:4802:32::15, etc.
- ✅ **COMPLETED**: Cloud Run domain mapping configured
- ⏳ **PENDING**: DNS propagation and accessibility verification
**DoD:** Domain acquired ✅, DNS configured (pending), domain accessible (pending DNS)
**Timeline:** Domain acquired ahead of schedule - DNS setup required
**Dependencies:** None - domain acquired, infrastructure ready
**Risk:** MEDIUM - DNS configuration by domain provider required

#### T59B - Cloud Run Domain Integration & SSL
**Priority:** P0 | **Estimate:** 4 hours | **Status:** ✅ **COMPLETED July 11, 2025**
**Dependencies:** T59A (Domain Acquisition) ✅ COMPLETED
- ✅ **COMPLETED**: Configure custom domain mapping in Cloud Run (`politics-watch.jp`)
- ✅ **COMPLETED**: Set up automatic SSL certificate provisioning via Google-managed certificates
- ✅ **COMPLETED**: Test HTTPS access (successful) ✅ **July 11, 2025**
- ✅ **COMPLETED**: Configure domain verification for Cloud Run
- ✅ **COMPLETED**: Implement HTTP to HTTPS redirects (auto-configured)
- ✅ **COMPLETED**: Validate SSL certificate chain (Google-managed cert active)
**DoD:** Infrastructure ready ✅, SSL configured ✅, HTTPS access verified ✅
**Timeline:** Fully completed July 11, 2025 - ahead of schedule
**Implementation:** Cloud Run service `seiji-watch-api-gateway-dev` with domain mapping `politics-watch.jp`
**✅ PRODUCTION READY:** https://politics-watch.jp accessible with valid SSL certificate

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

---

## EPIC 13: データ品質保証・リリース準備システム
**Target: July 22, 2025** | **Priority: P0** | **Status: 🆕 NEW**

*Comprehensive data quality assurance for production readiness - All tables quality enhancement*

現在のデータベース全体で品質問題が検出されており、MVP本格運用前に全テーブルの品質を完璧な水準まで向上させる必要がある。テーブル入れ替わりが緩やかな特性を考慮し、品質テスト・改修・検証の包括的なプロセスを確立する。

### Background & Justification
- **Current State**: 複数テーブルで品質問題（議員DB: 50.3%スコア）
- **Business Risk**: 本格運用開始時のデータ信頼性問題
- **User Impact**: 不正確な情報による政治分析の信頼性低下
- **Technical Debt**: 品質問題の後修正はコスト高・リスク高
- **Strategic Priority**: MVP成功には完璧なデータ品質が必須

#### T131 - 包括的データ品質評価システム
**Priority:** P0 | **Estimate:** 8 hours
- **全テーブル品質監査**:
  - `Members (議員)`: 744レコード → 目標品質95%以上
  - `Bills (法案)`: 全レコード → 目標品質90%以上  
  - `Sessions (会議)`: 全レコード → 目標品質95%以上
  - `Speeches (発言)`: 全レコード → 目標品質85%以上
  - `Parties (政党)`: 全レコード → 目標品質98%以上
  - `Issues (イシュー)`: 全レコード → 目標品質90%以上
- **品質メトリクス定義**:
  - 完全性（Completeness）: 必須フィールド充足率
  - 一意性（Uniqueness）: 重複・冗長データ検出率
  - 妥当性（Validity）: データ形式・範囲の正確性
  - 一貫性（Consistency）: テーブル間参照整合性
  - 正確性（Accuracy）: 情報源との一致度
  - 鮮度（Timeliness）: データ更新頻度・最新性
- **自動品質評価エンジン構築**
- **品質レポート・ダッシュボード生成**
**DoD:** 全テーブルの詳細品質評価が完了し、改善点が明確化

#### T132 - テーブル別品質改善計画実行
**Priority:** P0 | **Estimate:** 12 hours
- **Members (議員) 品質改善**:
  - 重複レコード手動レビュー・統合（自動化は行わない）
  - 政党名・選挙区表記の標準化
  - 必須フィールド（Name, House, Is_Active）100%充足確認
  - 議員プロフィール情報の信頼性向上
- **Bills (法案) 品質改善**:
  - 法案番号の重複・欠損チェック
  - 法案ステータスの一貫性確認
  - 提出者・所管省庁情報の正規化
  - 法案カテゴリ分類の精度向上
- **Sessions (会議) 品質改善**:
  - 会議日時の正確性検証
  - 会議種別・委員会名の標準化
  - 議事録との整合性確認
- **Speeches (発言) 品質改善**:
  - 発言者の議員テーブルとの整合性
  - 音声文字起こし精度の検証
  - 発言時刻・順序の正確性確認
- **Parties (政党) 品質改善**:
  - 政党名の表記統一・略称整理
  - 政党合併・分裂履歴の正確性
  - 議員テーブルとの参照整合性100%確保
- **Issues (イシュー) 品質改善**:
  - イシュータグの重複・類似チェック
  - 3層分類システムの整合性確認
  - 法案との関連付け精度向上
**DoD:** 各テーブルが目標品質水準に到達し、改善効果が測定可能

#### T133 - データ整合性・参照整合性強化
**Priority:** P0 | **Estimate:** 6 hours
- **テーブル間整合性チェック**:
  - Members ⇔ Parties 参照関係の100%整合性
  - Bills ⇔ Members（提出者）の整合性確認
  - Speeches ⇔ Members（発言者）の整合性確認
  - Sessions ⇔ Speeches の時系列整合性
  - Issues ⇔ Bills の関連付け妥当性
- **外部キー制約の論理的実装**（Airtable環境）
- **循環参照・デッドリンクの検出・修正**
- **データ型・フォーマットの統一化**
- **NULL値・空文字列の適切な処理**
**DoD:** 全テーブル間の整合性が保証され、データ整合性エラーゼロ達成

#### T134 - 本格運用向けデータガバナンス
**Priority:** P1 | **Estimate:** 6 hours
- **データ更新プロセスの標準化**:
  - 新規データ投入時の品質チェック自動化
  - データ更新権限・承認フローの確立
  - 更新履歴・監査ログの記録システム
- **データ品質SLA定義**:
  - 各テーブルの最低品質水準設定
  - 品質劣化時のアラート・対応手順
  - 定期品質監査スケジュール（週次・月次）
- **データバックアップ・復旧計画**:
  - 毎日の自動バックアップ実装
  - 品質劣化時の迅速な復旧手順
  - データ破損・喪失のリスク軽減策
- **ユーザー向け品質情報公開**:
  - データ品質メトリクスの透明性確保
  - 品質向上取り組みの定期レポート
  - ユーザーからの品質問題報告受付窓口
**DoD:** 持続可能なデータ品質管理体制が確立され、運用準備完了

#### T135 - リリース前品質検証・承認プロセス
**Priority:** P0 | **Estimate:** 8 hours
- **最終品質監査実施**:
  - 全テーブル品質スコア95%以上の確認
  - 重要データポイントの手動検証
  - ステークホルダーによる品質レビュー
- **本格運用シミュレーション**:
  - 実際のユーザーシナリオでのデータ精度テスト
  - 高負荷時のデータ整合性維持確認
  - エラーケースでの優雅な劣化テスト
- **品質承認チェックリスト**:
  - ✅ 全テーブル品質目標達成
  - ✅ テーブル間整合性100%確保
  - ✅ API応答精度・速度要件満足
  - ✅ フロントエンド表示品質確認
  - ✅ ユーザーテスト完了・問題なし
- **品質保証レポート作成**:
  - 品質改善の定量的効果測定
  - 残存リスク・制限事項の明文化
  - 運用開始後の品質維持計画
**DoD:** 全品質要件をクリアし、本格運用開始の最終承認取得

#### T136 - パフォーマンス最適化・スケーラビリティ確保
**Priority:** P1 | **Estimate:** 4 hours
- **大容量データでの性能確認**:
  - 744名議員データでの検索・表示速度
  - 数千件法案データでのフィルタリング性能
  - 同時アクセス時のレスポンス時間維持
- **クエリ最適化・インデックス戦略**:
  - 頻繁なクエリパターンの最適化
  - Airtable APIリクエスト効率化
  - フロントエンドキャッシュ戦略
- **将来拡張への対応**:
  - データ量増加に対する性能予測
  - スケールアウト戦略の準備
  - リソース使用量モニタリング
**DoD:** 現在・将来のデータ量に対する性能要件をクリア

#### T137 - 品質保証自動化・CI/CD統合
**Priority:** P1 | **Estimate:** 4 hours
- **継続的品質監視システム**:
  - データ品質の自動テスト・CI/CD統合
  - 品質劣化の即座検出・アラート
  - 品質レポートの自動生成・配信
- **回帰テスト・品質ゲート**:
  - データ更新時の品質回帰防止
  - デプロイ前の必須品質チェック
  - 品質基準未達時の自動デプロイ阻止
- **長期品質トレンド分析**:
  - 品質メトリクスの時系列追跡
  - 品質改善・劣化トレンドの可視化
  - 予防的品質管理の実現
**DoD:** 品質保証プロセスが完全自動化され、持続的改善サイクル確立

**EPIC 13 Summary:**
- **Total Estimated:** 48 hours
- **Critical Path:** T131→T132→T133→T135 (評価→改善→整合性→最終検証)
- **Success Metrics:** 
  - 全テーブル品質スコア90%以上達成
  - データ整合性エラーゼロ
  - API応答時間<200ms維持
  - ユーザーテスト満足度95%以上
- **Quality Gates:** 各チケット完了時の品質基準クリア必須
- **Risk Mitigation:** 段階的改善、バックアップ保持、ロールバック準備
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

## EPIC 9: 法的コンプライアンス - 利用規約・プライバシーポリシー実装
**Target:** 2025年7月15日 | **Total Estimate:** 12 hours | **Dependencies:** なし

### Background
Diet Issue Trackerの本格運用に向けて、法的コンプライアンス要件を満たす利用規約（Terms of Service）およびプライバシーポリシー（Privacy Policy）の実装が必要。個人情報保護法、公職選挙法等の日本国法に準拠し、政治的中立性を保持した文書および表示システムを構築する。

### Business Value
- **法的リスク軽減**: 個人情報保護法・公職選挙法遵守による法的リスク回避
- **ユーザー信頼獲得**: 透明性の高いプライバシー方針によるユーザー信頼向上
- **運用安定性**: 明確な利用規約による適切なサービス運用基盤確立
- **政治的中立性担保**: 選挙法準拠による政治的中立性の明確化

### Success Criteria
- ✅ 個人情報保護法完全準拠の文書作成
- ✅ 政治的中立性を保持した利用規約策定
- ✅ アクセシブルな表示UI実装（WCAG 2.1 AA準拠）
- ✅ モバイルファーストレスポンシブ対応
- ✅ フッター・ヘッダーからの適切なリンク設置

---

#### T68 - 法的文書作成・法務レビュー ✅ COMPLETED
**Priority:** P1 | **Estimate:** 6 hours | **Status:** COMPLETED | **Actual:** 6 hours

**作業内容:**
- 利用規約ドラフト作成（日本国法準拠）
- プライバシーポリシードラフト作成（個人情報保護法対応）
- 政治的中立性条項の策定（公職選挙法遵守）
- 知的財産権条項（憲法第40条準拠）
- 免責事項・サービス変更条項の策定

**技術要件:**
- Markdown形式での文書管理
- バージョン管理対応（Git）
- 多言語対応準備（将来の英語版）

**DoD:**
- 法的要件を満たす利用規約文書完成
- 個人情報保護法準拠のプライバシーポリシー完成
- 政治的中立性が明確に記載された条項
- 法務担当者による内容確認・承認

**参照文書:**
- `/docs/legal-compliance-requirements.md`
- 個人情報保護法（改正版 2022年4月施行）
- 公職選挙法第146条（文書図画の配布制限）

---

#### T69 - 法的文書表示UI実装 ✅ COMPLETED
**Priority:** P1 | **Estimate:** 4 hours | **Status:** COMPLETED | **Actual:** 4 hours

**作業内容:**
- `/terms` 利用規約ページコンポーネント開発
- `/privacy` プライバシーポリシーページコンポーネント開発
- アクセシブルデザイン実装（WCAG 2.1 AA準拠）
- レスポンシブレイアウト対応
- ふりがな表示機能（重要部分）

**技術仕様:**
- Next.js静的ページ生成
- TypeScript型安全性確保
- Tailwind CSSスタイリング
- 色覚バリアフリー対応

**機能要件:**
- 目次・セクション分け
- ページ内検索機能
- 印刷対応レイアウト
- 更新履歴表示

**DoD:**
- アクセシビリティ監査スコア 95%+
- モバイル最適化スコア 90%+
- ページ読み込み速度 < 2秒
- 全デバイスでの表示確認完了

**API Requirements:**
- 静的ページ生成（getStaticProps）
- SEOメタデータ設定
- 構造化データ（JSON-LD）対応

---

#### T70 - サイト統合・公開準備 ✅ COMPLETED
**Priority:** P2 | **Estimate:** 2 hours | **Status:** COMPLETED | **Actual:** 2 hours

**作業内容:**
- フッターコンポーネントにリンク追加
- ヘッダーナビゲーションへのリンク追加
- 内部クロスリファレンス整備
- 本番環境デプロイ・動作確認

**統合要件:**
- 既存Layoutコンポーネントとの統合
- ナビゲーション一貫性確保
- ユーザーフロー最適化

**検証項目:**
- 全ページからのリンクアクセス確認
- SEO設定の動作確認
- アクセシビリティ最終検証
- モバイル・デスクトップ動作確認

**DoD:**
- フッター・ヘッダーリンク実装完了
- 本番環境での正常表示確認
- Google Lighthouse スコア 90%+
- 法的文書への適切なアクセス導線確立

**Deployment:**
- Staging環境での事前検証
- Production環境への段階的デプロイ
- 404エラー・リンク切れチェック

---

**EPIC 9 Total Progress: 3/3 tickets completed** ✅ **COMPLETED**

**Risk Mitigation:**
- 法務レビュー遅延: 外部法務相談体制準備
- 文書複雑化: シンプルで理解しやすい条項策定
- アクセシビリティ: 段階的改善・専門監査実施

---

## 🚨 緊急対応チケット: EPIC 7 UI Verification Issues
**Date Added:** July 11, 2025  
**Priority:** P0 - CRITICAL  
**Context:** EPIC 7完全実装済みだが、localhost接続問題によりUI確認不可能

### Background
EPIC 7 (3-Layer Issue Categorization System) の全実装が完了したが、macOSでのlocalhost接続問題により、ユーザーがブラウザでUI確認できない状況が発生。プロセスは起動するがポートがlistenしない症状を呈している。

#### T88 - localhost接続問題診断・解決 🚨 CRITICAL
**Priority:** P0 | **Estimate:** 2 hours | **Status:** IMMEDIATE ACTION REQUIRED
- **o3推奨診断手順実行**:
  - プロセス生存確認: 最高冗長度サーバー起動 + リアルタイムポート監視
  - クラッシュ原因調査: Console.app確認、インポートエラー特定  
  - ネットワーク設定検証: IPv4/IPv6確認、隠れプロセス調査
- **macOS固有問題確認**:
  - Quarantine属性チェック (`xattr -l $(which python3)`)
  - Rosetta/arm64バイナリ競合確認
  - Application Firewall/PF設定確認
- **根本原因特定**: 段階的診断により"プロセス起動するがbind()失敗"の原因解明
**DoD:** 根本原因が特定され、documented resolutionが確立される

#### T89 - EPIC 7デモ環境構築 🚨 CRITICAL  
**Priority:** P0 | **Estimate:** 1 hour | **Status:** IMMEDIATE ACTION REQUIRED
- **確実動作する代替デモサーバー実装**:
  - PythonのHTTPServerベース実装（依存関係最小化）
  - Port 8080での確実な起動確保
  - IPv4/IPv6両対応でのバインド設定
- **EPIC 7カテゴリシステム完全デモ**:
  - CAP分類L1/L2階層の視覚的表示
  - インタラクティブな階層ナビゲーション
  - レスポンシブデザインでのモバイル対応
- **ブラウザ直接アクセス環境**:
  - HTMLページでのカテゴリツリー表示
  - JavaScript動的ローディング
  - モックデータ統合表示
**DoD:** ユーザーがhttp://127.0.0.1:8080でEPIC 7の完全な成果物を確認可能

### 実行計画
1. **Phase 1 (45分)**: o3診断手順による根本原因特定
2. **Phase 2 (30分)**: 迅速デモ実装（HTTPServer + HTML/JS）
3. **Phase 3 (15分)**: ブラウザUI確認完了・ドキュメント更新

### Dependencies
- EPIC 7完全実装済み ✅ (T71-T79すべて完了)
- CAP分類データ準備済み ✅ 
- APIエンドポイント実装済み ✅
- React UIコンポーネント実装済み ✅

### Success Criteria
- ブラウザでEPIC 7のCAP-based 3層カテゴリシステムが視覚的に確認できる
- L1→L2階層ドリルダウンが動作する
- 国際標準準拠の政策分類が日本語で表示される
- レスポンシブデザインがモバイルで機能する

---

## EPIC 10: イシュー個別ページAPI実装 - Critical Gap Resolution
**Target: July 11, 2025** | **Priority: P0** | **Status: 🚨 NEW - CRITICAL**

*緊急対応: フロントエンド実装済みだが対応するバックエンドAPI未実装によるユーザー体験阻害の解消*

### Background & Critical Issue
- **Problem**: イシューカードクリック時に404エラー発生（個別イシューAPIエンドポイント未実装）
- **Impact**: 完全実装済みのフロントエンド機能が使用不可、TOPページからのユーザージャーニー断絶
- **Root Cause**: 開発計画でのAPIエンドポイント実装漏れ（Kanban API実装済み、個別詳細API未実装）
- **Urgency**: MVP公開前必須修正項目

#### T92 - 個別イシューAPI実装 🚨 CRITICAL
**Priority:** P0 | **Estimate:** 4 hours | **Status:** IMMEDIATE ACTION REQUIRED
- **`GET /api/issues/{issue_id}` エンドポイント実装**:
  - Airtable Issues base からの個別レコード取得
  - フロントエンドが期待するレスポンス形式に変換
  - 関連エンティティ（PolicyCategory, IssueTags）の正規化
- **エラーハンドリング実装**:
  - 404 Not Found適切処理（存在しないissue_id）
  - 500 Internal Server Error処理（Airtable接続エラー等）
  - レスポンス形式統一化
- **データ変換ロジック**:
  - Airtable Fields形式 → フロントエンドIssue型変換
  - KanbanAPIとの一貫性確保
  - 既存simple_server.pyパターン流用
**DoD:** `/issues/ISS-096`ページで正常にイシュー詳細が表示される

#### T93 - 関連法案API実装 🚨 CRITICAL  
**Priority:** P0 | **Estimate:** 3 hours | **Status:** IMMEDIATE ACTION REQUIRED
- **`GET /api/issues/{issue_id}/bills` エンドポイント実装**:
  - 指定イシューの関連法案一覧取得
  - 関連度スコア付きレスポンス
  - ページネーション対応（デフォルト20件）
- **関連性データ処理**:
  - Issue.related_bills からBillレコード取得
  - 法案進捗状況（stage）の動的判定
  - 法案-イシュー関係性の双方向整合性チェック
- **パフォーマンス最適化**:
  - 一括取得クエリ実装
  - レスポンス時間 ≤200ms確保
  - 適切なキャッシング戦略
**DoD:** イシュー詳細ページ「関連法案」タブで法案一覧が正常表示される

#### T94 - データフォーマット統一化・概念整理対応 🔄 CONCEPT UPDATE
**Priority:** P0 | **Estimate:** 2 hours | **Status:** SPECIFICATION UPDATE REQUIRED
- **概念区別の実装反映**:
  - Issue（政策課題）vs PolicyCategory（政策分野）の明確化
  - `Issue.category_id` → `Issue.policy_category_id` 変更
  - レスポンス内での概念表現統一
- **API仕様書更新**:
  - `/docs/issue-feature-specification.md` 準拠
  - OpenAPI仕様書更新
  - レスポンス例の修正・明確化
- **既存コードの概念整理**:
  - 変数名・フィールド名の統一
  - コメント・ドキュメントの概念修正
  - フロントエンド型定義との整合性確保
**DoD:** イシュー機能全体で概念が一貫して正しく表現される

#### T95 - 統合テスト・品質保証 ⚡ VALIDATION
**Priority:** P0 | **Estimate:** 2 hours | **Status:** INTEGRATION TESTING
- **API統合テスト**:
  - 個別イシューAPI + 関連法案APIの連携動作確認
  - KanbanAPI → 個別ページAPIのデータ一貫性検証
  - エラーケース網羅テスト（存在しないID、Airtable接続エラー等）
- **E2E ユーザージャーニーテスト**:
  - TOPページ → イシューカードクリック → 詳細ページ表示
  - 詳細ページ内タブ切り替え動作
  - 「戻る」ボタン動作確認
- **パフォーマンス検証**:
  - API応答時間計測（目標: ≤200ms）
  - フロントエンド表示速度確認（目標: ≤1秒）
  - 同時接続テスト
**DoD:** 完全なユーザージャーニーが問題なく動作し、パフォーマンス要件を満たす

**EPIC 10 Summary:**
- **Total Estimated:** 11 hours
- **Target Completion:** July 11, 2025 (Same Day - Critical)
- **Critical Path:** T92 → T93 → T95 (API実装 → 関連法案 → 統合テスト)
- **Parallel Development:** T94 (概念整理) 並行実行可能

**Key Features Delivered:**
- 完全動作するイシュー個別ページ
- TOPページからのシームレスナビゲーション
- 概念的に正しいイシュー機能実装
- 完全なユーザー体験の実現

**Dependencies:**
- Kanban API実装済み ✅ (正常動作確認済み)
- フロントエンド個別ページ実装済み ✅ (UIコンポーネント完成)
- Airtable Issues/Bills base ready ✅
- 仕様書完成 ✅ (`/docs/issue-feature-specification.md`)

**Success Metrics:**
- TOPページ → イシュー詳細ページ遷移成功率: 100%
- API応答時間: ≤200ms (p95)
- エラー率: ≤1%
- ユーザージャーニー完了率: 100%

**Risk Mitigation:**
- 既存Kanban API実装パターン流用による開発スピード向上
- Simple server構造による複雑性回避
- 段階的実装・テストによる品質確保
- 概念整理の並行実行による効率化

---

## EPIC 11: 実データ統合 & プロダクション準備 - Critical Data Integration
**Target: July 14, 2025** | **Priority: P0** | **Status: 🚨 NEW - CRITICAL**

*緊急対応: 収集済みデータの統合によるプロダクト完成*

### Background & Critical Discovery
- **Problem**: 2025年7月9日に200件の法案データ + 投票データが収集済みだが、プロダクトに統合されていない
- **Impact**: localhostで空白状態、実際のデータが表示されない、MVPとして不完全
- **Root Cause**: スクレイピング → データベース投入 → API連携のパイプライン断絶
- **Urgency**: 参院選公開(7/22)まで11日、データ統合必須

### 実データ収集状況分析
**✅ 収集完了**: `/services/ingest-worker/production_scraping_june2025_20250709_032237.json`
- **実行日時**: 2025-07-09 03:22:37
- **対象期間**: 2025年6月1日〜30日 (第217回国会)
- **収集実績**:
  - 法案データ: **200件** (所得税法改正、地方税法改正、重要電子計算機法案等)
  - 投票セッション: **3件**
  - 投票レコード: **60件** (議員別投票結果)
  - 実行時間: 0.3秒 (高効率処理)
  - 成功率: 100% (エラー0件)

#### T96 - 収集済みJSONデータのAirtable投入 🚨 CRITICAL
**Priority:** P0 | **Estimate:** 6 hours | **Status:** IMMEDIATE ACTION REQUIRED
- **法案データ構造化投入**:
  - 200件の法案レコードをAirtable Bills baseに投入
  - 構造化: bill_id, title, status, stage, category, submitter等
  - データ正規化: 日付形式統一、カテゴリ標準化
- **投票データ投入**:
  - 3件の投票セッション + 60件の投票レコードをVotes/VoteResults baseに投入
  - 議員-政党-投票結果の関係性構築
  - 重複排除とデータ品質検証
- **データ品質保証**:
  - 投入前データバリデーション
  - 文字エンコーディング確認 (UTF-8)
  - 必須フィールドの欠損値チェック
**DoD:** 200件の法案データがAirtableで正常に参照でき、API経由で取得可能

#### T97 - API Gateway実データ連携修正 🚨 CRITICAL
**Priority:** P0 | **Estimate:** 4 hours | **Status:** IMMEDIATE ACTION REQUIRED
- **simple_server.py修正**:
  - モックデータからAirtable実データ取得に変更
  - `/api/issues/kanban` エンドポイントで実際のイシューデータ返却
  - `/api/bills` エンドポイントで実際の法案データ返却
- **Airtable接続強化**:
  - Airtable API client実装済みコードの活用
  - 適切なエラーハンドリング (404, 500)
  - レスポンス形式統一 (フロントエンドと互換性確保)
- **パフォーマンス最適化**:
  - キャッシング戦略実装 (TTL: 30分)
  - レスポンス時間≤200ms確保
  - 同時接続数制限対応
**DoD:** `/api/issues/kanban` で実際の法案由来イシューが返却され、フロントエンドで表示される

#### T98 - EPIC 10完了: 個別イシューAPIエンドポイント 🔄 CONTINUATION
**Priority:** P0 | **Estimate:** 4 hours | **Status:** CONTINUATION OF EPIC 10
- **`GET /api/issues/{issue_id}` 完全実装**:
  - 実データベースからの個別イシュー取得
  - 関連法案データの正規化取得
  - カテゴリ・タグ情報の統合表示
- **`GET /api/issues/{issue_id}/bills` 実装**:
  - 指定イシューの関連法案一覧
  - 法案進捗状況の動的判定
  - ページネーション対応 (デフォルト20件)
- **エラーハンドリング完全実装**:
  - 404 Not Found (存在しないissue_id)
  - 500 Internal Server Error (Airtable接続エラー)
  - レスポンス形式統一
**DoD:** TOPページ → イシューカードクリック → 詳細ページの完全なユーザージャーニーが動作

#### T99 - フロントエンド実データ表示確認 ⚡ VALIDATION
**Priority:** P0 | **Estimate:** 3 hours | **Status:** DATA VALIDATION
- **Kanbanボード実データ確認**:
  - 200件法案から生成されたイシューの表示確認
  - ステージ分類 (審議前/審議中/採決待ち/成立) の正確性
  - イシューカード情報の完全性確認
- **詳細ページ実データ確認**:
  - 個別イシューページの正常表示
  - 関連法案一覧の正確性
  - UI/UXの実データでの適切性
- **検索機能実データ確認**:
  - 法案タイトル・内容での検索動作
  - フィルタリング機能の正常動作
  - レスポンス速度確認 (≤1秒)
**DoD:** 実際のデータでの完全なユーザー体験が確認され、UIに不具合がない

#### T100 - データ品質検証 & UI調整 📊 QUALITY ASSURANCE
**Priority:** P1 | **Estimate:** 3 hours | **Status:** FINAL POLISH
- **データ品質メトリクス測定**:
  - 法案データの完全性: 必須フィールド充足率
  - カテゴリ分類の適切性: 手動サンプリング確認
  - 日本語表示の正確性: 文字化け・表記揺れチェック
- **UI調整**:
  - 実データでの表示レイアウト最適化
  - 長いタイトルの省略表示調整
  - レスポンシブデザインの実データでの確認
- **パフォーマンス最終確認**:
  - 200件データでのページロード速度
  - 同時接続時のレスポンス安定性
  - メモリ使用量・CPU負荷確認
**DoD:** プロダクトが実データで完全に動作し、MVP品質要件を満たす

**EPIC 11 Summary:**
- **Total Estimated:** 20 hours
- **Target Completion:** July 14, 2025 (3日間集中実行)
- **Critical Path:** T96 → T97 → T98 → T99 (データ投入 → API修正 → エンドポイント → 確認)
- **Parallel Development:** T100 (品質検証) 並行実行可能

**Key Features Delivered:**
- 200件の実法案データによる完全動作MVP
- 実際の国会データを用いたKanbanボード
- 完全なイシュー詳細ページ機能
- プロダクション品質のデータ統合システム

**Dependencies:**
- 収集済みJSONデータファイル ✅ (112KB, 2025-07-09実行)
- Airtable API統合基盤 ✅ (実装済み)
- フロントエンドUI ✅ (完成済み)
- API Gateway基盤 ✅ (実装済み)

**Success Metrics:**
- localhost実データ表示成功率: 100%
- API応答時間: ≤200ms (p95)
- データ完全性: ≥95%
- ユーザー体験: エラー率≤1%

**Risk Mitigation:**
- 既存実装パターン流用による開発スピード確保
- 段階的データ投入によるリスク最小化
- 並行品質検証による早期問題発見
- ロールバック可能な投入プロセス設計

**Immediate Action Required:**
1. **T96開始**: 収集済みデータのAirtable投入 (最優先)
2. **環境確認**: .env.local設定とAirtable接続確認
3. **データバリデーション**: 投入前のデータ品質チェック

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
*T88-T89 Added: July 11, 2025 - EPIC 7 UI Verification Critical Issues*
*EPIC 10 Added: July 11, 2025 - Issue Individual Page API Implementation - Critical Gap Resolution*
*EPIC 11 Added: July 11, 2025 - Real Data Integration & Production Readiness - Critical Data Pipeline Completion*

---

## EPIC 12: TOPページ Active Issues 横ストリップ実装 - UX改善
**Target: July 14, 2025** | **Priority: P0** | **Status: 🆕 NEW**

*TOPページKanbanボードから横スクロールストリップへの仕様変更による初回訪問者エンゲージメント最適化*

### Background & Design Rationale
- **Current Problem**: 4列Kanbanボードが初回ユーザーには情報過多、離脱率高い
- **UX Goal**: 5秒で「いま何が議論されているか」を把握できる直感的UI
- **Design Decision**: 横スクロール1行ストリップ（Netflix/App Store UI pattern）
- **Target Audience**: 政治に詳しくない一般ユーザーのエンゲージメント向上

### Technical Specifications
- **表示対象**: ステータス `deliberating` + `vote_pending` のみ（緊急性の高いイシューに特化）
- **レイアウト**: 横スクロール1行、280px固定幅カード、scroll-snap対応
- **表示件数**: 8-12件（API制限）
- **色覚バリアフリー**: Green #27AE60 (審議中), Yellow #F1C40F (採決待ち)

#### T101 - Active Issues API エンドポイント実装
**Priority:** P0 | **Estimate:** 2 hours | **Status:** NEW
- **新API実装**: `GET /api/issues?status=in_view&limit=12`
- **ステータスフィルタリング**: `deliberating`, `vote_pending` のみ返却
- **レスポンス最適化**: フロントエンド要求仕様に合わせたデータ構造
- **既存API保持**: `/api/issues/kanban` は他ページで利用継続
- **パフォーマンス**: レスポンス時間 ≤200ms, キャッシング30分TTL
**DoD:** 横ストリップ用の最適化されたAPIエンドポイントが利用可能

#### T102 - ActiveIssuesStrip コンポーネント実装
**Priority:** P0 | **Estimate:** 4 hours | **Status:** NEW
- **新コンポーネント**: `components/ActiveIssuesStrip.tsx` 
- **横スクロール実装**: `overflow-x-auto`, `scroll-snap-type: x mandatory`
- **280px固定幅カード**: レスポンシブ対応（モバイルでも固定幅維持）
- **グラデーションフェード**: 左右端での視覚的ヒント
- **アクセシビリティ**: キーボードナビゲーション、ARIA labels対応
**DoD:** Netflix風横スクロールUIが全デバイスで正常動作

#### T103 - IssueCard リデザイン実装  
**Priority:** P0 | **Estimate:** 3 hours | **Status:** NEW
- **カード仕様**: 280px × auto height, コンパクトデザイン
- **ステータスバッジ**: 右上角に色分けバッジ（審議中/採決待ち）
- **情報密度最適化**: 
  - タイトル（2行省略, 16px bold）
  - 日期間ピル（YYYY年M月D日-形式）
  - タグチップ（最大3個、グレー背景）
  - 関連法案カプセル（件数表示 + 詳細リンク）
  - 最終更新タイムスタンプ（12px グレー）
- **インタラクション**: ホバーで詳細プレビュー、クリックで個別ページ遷移
**DoD:** 情報豊富で直感的な280px横カード完成

#### T104 - TOPページ統合・KanbanからStrip置換
**Priority:** P1 | **Estimate:** 2 hours | **Status:** NEW  
- **pages/index.tsx 修正**: KanbanBoard → ActiveIssuesStrip 置換
- **セクション見出し変更**: 「直近1ヶ月の議論」→「いま議論されている問題」
- **レイアウト調整**: 検索セクションとの縦間隔最適化
- **SEO対応**: セマンティックHTML, structured data更新
- **パフォーマンス**: SSG事前生成対応
**DoD:** TOPページで新しい横ストリップが正常表示され、UX流れが自然

#### T105 - インタラクション・アニメーション実装
**Priority:** P1 | **Estimate:** 2 hours | **Status:** NEW
- **初回訪問アニメーション**: 最初のカードがslide-inで注意喚起
- **スクロールヒント**: 横スクロール可能であることの視覚的示唆
- **ホバーエフェクト**: デスクトップでのカードホバー時詳細プレビュー
- **タッチジェスチャー**: モバイルでのスワイプ操作最適化
- **トランジション**: カード間移動のスムーズアニメーション
**DoD:** 直感的で魅力的なインタラクション体験が実現

#### T106 - E2E テスト・品質保証
**Priority:** P0 | **Estimate:** 1 hour | **Status:** NEW
- **横スクロール機能テスト**: マウス、タッチ、キーボード操作
- **レスポンシブ検証**: 375px→1440px全デバイス確認  
- **アクセシビリティ監査**: WCAG 2.1 AA準拠、Lighthouse ≥95
- **パフォーマンステスト**: Core Web Vitals, 初期表示速度
- **ブラウザ互換性**: Chrome, Safari, Firefox, Edge
**DoD:** 全品質要件を満たし本番デプロイ可能

**EPIC 12 Summary:**
- **Total Estimated:** 14 hours
- **Target Completion:** July 14, 2025 (3日間)
- **Critical Path:** T101 → T102 → T103 → T104 (API → UI基盤 → カード → 統合)
- **Parallel Development:** T105 (アニメーション), T106 (QA)

**Key Features Delivered:**
- Netflix風横スクロール「いま議論されている問題」ストリップ
- 初回ユーザー向け5秒理解可能なUI
- 緊急性の高いイシューに特化した情報表示
- 全デバイス対応のスムーズインタラクション

**Dependencies:**
- EPIC 10 (個別イシューAPI) 完了済み ✅ 
- EPIC 11 (実データ統合) 完了必須 🔄
- 既存 `/api/issues` エンドポイント基盤 ready ✅

**Success Metrics:**
- TOPページ滞在時間: 10秒 → 45秒+
- イシュー詳細遷移率: 5% → 20%+
- 初回訪問離脱率: 70% → 45%以下
- 横スクロール利用率: 80%+

**Risk Mitigation:**
- 既存Kanban機能保持: 他ページでは従来UI継続利用
- 段階的リリース: フィーチャーフラグによるA/Bテスト可能
- パフォーマンス監視: Core Web Vitals リアルタイム測定
- ユーザビリティテスト: リリース前のユーザー検証

**Design Rationale:**
- **認知負荷軽減**: 4列→1行により情報処理負荷削減
- **緊急性の可視化**: アクティブなイシューのみ表示で重要度明確化  
- **親和性向上**: 一般的なWebアプリUIパターン採用
- **エンゲージメント促進**: スクロール行動による探索意欲向上

---

## EPIC 13: データ品質管理・権限修正対応
**Target: July 12-14, 2025** | **Priority: P0** | **Status: 🚧 NEW**

### Background
データ診断により以下の重要な問題が判明：
- Airtableアクセス権限問題（複数テーブルで403エラー）
- 議員データ：0件（必須データ欠損）
- 発言データ：0件（AI分析機能停止）
- イシューデータ：0件（コア機能停止）
- 法案データ：100件（目標150件に対し66%）

### Target State
- 全コアテーブルにデータが存在し、MVP機能が正常動作
- データ品質管理体制の確立

#### T107 - Airtable権限確認・テスト実行 🚨 IMMEDIATE
**Priority:** P0 | **Estimate:** 1 hour | **Status:** NEW
- **権限修正後検証**:
  - 全9テーブルへのアクセス確認（Members, Speeches, Issues等）
  - API経由でのCRUD操作テスト
  - データ診断スクリプト再実行
- **データベース接続テスト**:
  - AirtableClientの初期化成功確認
  - 各テーブルからのサンプルデータ取得
  - エラーログ・レスポンス時間記録
**DoD:** 全テーブルに正常アクセス可能、403エラー解決確認

#### T108 - 議員データ収集・投入実行 📊 CRITICAL
**Priority:** P0 | **Estimate:** 4 hours | **Status:** NEW
- **スクレイピング実行**:
  - 既存のDietScraperを使用した議員データ収集
  - 目標：現職議員50件以上の基本情報
  - 政党情報・選挙区情報の包括的収集
- **Airtable投入**:
  - AirtableClientを使用した自動投入
  - 重複排除・データ正規化処理
  - Members/Partiesテーブルへの構造化データ格納
- **データ品質検証**:
  - 必須フィールド充足率95%以上
  - 政党・選挙区データの整合性確認
**DoD:** 50件以上の議員データがAirtableに正常格納され、API経由で取得可能

#### T109 - 発言データ初期収集・STT処理 🎤 FOUNDATION
**Priority:** P1 | **Estimate:** 6 hours | **Status:** NEW
- **議事録データ収集**:
  - 最新の委員会・本会議議事録収集（限定スコープ）
  - 音声データのダウンロード・前処理
  - 発言者情報とのマッピング
- **STT処理実行**:
  - OpenAI Whisperを使用した音声→テキスト変換
  - 目標：100件の発言データ生成
  - 信頼度・品質メトリクス記録
- **Airtable投入**:
  - Speechesテーブルへの構造化データ格納
  - Meeting/Member関連付け
  - AI分析用メタデータ設定
**DoD:** 100件の発言データが高品質でAirtableに格納され、AI分析基盤準備完了

#### T110 - イシューデータ生成・LLM抽出 🧠 AI-POWERED
**Priority:** P1 | **Estimate:** 4 hours | **Status:** NEW
- **法案からのイシュー抽出**:
  - 既存100件の法案データを対象
  - OpenAI/Claude APIを使用したイシュー抽出
  - 政策分野・緊急度・影響度の自動分類
- **3層カテゴリシステム適用**:
  - CAP分類に基づくL1/L2/L3カテゴリ割り当て
  - イシュータグの自動生成・関連付け
  - 階層構造データの整合性確保
- **Airtable投入・関連付け**:
  - Issues/IssueCategories/IssueTagsテーブル投入
  - 法案データとの双方向リンク設定
  - 検索・フィルタリング用インデックス作成
**DoD:** 法案データから50件以上のイシューが自動抽出され、3層分類システムで管理可能

#### T111 - データ品質管理体制確立 📈 MONITORING
**Priority:** P2 | **Estimate:** 3 hours | **Status:** NEW
- **定期診断システム**:
  - データ品質診断スクリプトの自動化
  - 日次/週次でのデータ完全性チェック
  - アラート・レポート機能実装
- **データバリデーション強化**:
  - 投入前データの自動検証ルール
  - 異常値・欠損値の検出・処理
  - データ整合性チェック（リレーション）
- **運用ダッシュボード**:
  - データ収集状況の可視化
  - 品質メトリクスのリアルタイム監視
  - 問題発生時の迅速対応手順
**DoD:** 持続可能なデータ品質管理システムが稼働し、高品質データが保証される

#### T112 - API・フロントエンド実データ確認 ✅ VALIDATION
**Priority:** P0 | **Estimate:** 2 hours | **Status:** NEW
- **API エンドポイント確認**:
  - 全APIで実データが正常に返却されることを確認
  - レスポンス形式・パフォーマンスの検証
  - エラーハンドリングの動作確認
- **フロントエンド表示確認**:
  - 法案・議員・イシュー情報の正常表示
  - 検索・フィルタリング機能の動作確認
  - レスポンシブデザインでの表示品質
- **統合テスト**:
  - エンドツーエンドのユーザージャーニー確認
  - データ整合性・表示一貫性の検証
  - パフォーマンス・ユーザビリティ確認
**DoD:** 全機能で実データが正常表示され、MVP品質要件を満たす

**EPIC 13 Summary:**
- **Total Estimated:** 20 hours
- **Target Completion:** July 14, 2025 (3日間)
- **Critical Path:** T107 → T108 → T109 → T110 → T112 (権限確認 → 議員データ → 発言データ → イシューデータ → 統合確認)
- **Parallel Development:** T111 (データ品質管理)

**Key Objectives:**
- 全コアテーブルのデータ充実（法案150件、議員50件、発言100件、イシュー50件）
- データ品質管理体制の確立
- MVP機能の完全動作確認

**Success Criteria:**
- Airtable全テーブルアクセス可能
- 議員データ50件以上収集・投入完了
- 発言データ100件STT処理完了
- イシューデータ50件LLM抽出完了
- フロントエンドでの実データ正常表示
- データ品質95%以上維持

**Dependencies:**
- Airtable API権限修正（完了済み）
- EPIC 11（実データ統合）基盤
- 既存スクレイピング・AI処理パイプライン

---

## EPIC 14: Hybrid Ingestion Pipeline - NDL API × Whisper

**Goal**: Implement cost-optimized hybrid data ingestion combining NDL Minutes API for historical data (第217回国会まで) and Whisper STT for real-time processing.

**Timeline**: 4 weeks  
**Estimated Effort**: 32 hours  
**Priority**: Medium (Post-MVP enhancement)

### Background
Current STT-only approach for all historical meetings incurs high costs (~$85/month). NDL API provides free access to structured meeting minutes for sessions up to 第217回国会 (≤ 2025-06-21), enabling 75% cost reduction.

### Technical Approach
- **Historical Path**: NDL Minutes API → JSON processing → Airtable
- **Real-time Path**: Diet TV → Whisper STT → Airtable  
- **Decision Logic**: Date-based routing (≤ 2025-06-21 vs ≥ 2025-06-22)

#### T120 - NDL API Client Development ⏳ PENDING
**Objective**: Build rate-limited HTTP client for NDL Minutes API  
**Acceptance Criteria**:
- [ ] NDL API client with ≤3 req/s rate limiting
- [ ] JSON response parser for meeting minutes
- [ ] Error handling with exponential backoff
- [ ] Unit tests for API integration

**Files**: `services/ingest-worker/src/collectors/ndl_api_client.py`  
**Estimate**: 8 hours  
**Dependencies**: None

#### T121 - Data Mapping & Schema Unification ⏳ PENDING  
**Objective**: Map NDL API data format to existing Airtable schema
**Acceptance Criteria**:
- [ ] NDL meeting format → Airtable Speeches/Meetings mapping
- [ ] Speaker identification & party affiliation matching
- [ ] Bill discussion extraction from speech content
- [ ] Unified data interface for both NDL + Whisper sources

**Files**: `services/ingest-worker/src/pipeline/ndl_data_mapper.py`  
**Estimate**: 10 hours  
**Dependencies**: T120

#### T122 - Historical Data Batch Processing ⏳ PENDING
**Objective**: Ingest all 第217回国会 meetings via NDL API  
**Acceptance Criteria**:
- [ ] Batch ingestion script for meeting range (2025-01-24 〜 2025-06-21)
- [ ] Progress tracking with resume capability
- [ ] Data validation & quality checks
- [ ] Performance monitoring & cost tracking

**Files**: `services/ingest-worker/src/batch/historical_ingestion.py`  
**Estimate**: 8 hours  
**Dependencies**: T120, T121

#### T123 - Pipeline Routing Logic ⏳ PENDING
**Objective**: Implement date-based routing between NDL API and Whisper STT  
**Acceptance Criteria**:
- [ ] Meeting date analysis (≤ 2025-06-21 vs ≥ 2025-06-22)
- [ ] Automatic pipeline selection logic
- [ ] Fallback mechanisms for edge cases
- [ ] Manual override for specific meetings

**Files**: `services/ingest-worker/src/pipeline/ingestion_router.py`  
**Estimate**: 6 hours  
**Dependencies**: T120, T121, T122

**EPIC 14 Summary:**
- **Total Tickets**: 4
- **Total Effort**: 32 hours
- **Success Metrics**: 75% cost reduction, 100% historical data coverage
- **Risk Mitigation**: Phased rollout, fallback to existing STT pipeline

---

## EPIC 15: Issue Notification System — MVP

**Goal**: Enable users to monitor legislative progress through email notifications

**Timeline**: 3 weeks  
**Estimated Effort**: 32 hours  
**Priority**: High (User engagement enhancement)

### Background
Transform passive browsing into active political monitoring. Users can "watch" specific issues and receive daily digest emails when bills progress through legislative stages or related committee meetings are scheduled.

### Technical Approach
- **Event Detection**: Poll Airtable for bill stage changes and new meetings
- **Notification Service**: Cloud Run service triggered by Cloud Scheduler
- **Email Delivery**: SendGrid for reliable email delivery with tracking
- **Frontend**: Watch button on issue pages + header quick-watch modal

#### T124 - Database Schema & Event Detection ❌ NOT IMPLEMENTED
**Objective**: Create subscription and event tracking tables with change detection
**Acceptance Criteria**:
- [ ] `subscriptions` table with email validation and confirmation flow
- [ ] `issue_events` table with fingerprint-based deduplication
- [ ] Event detection logic for bill stage changes and meeting creation
- [ ] Idempotency handling to prevent duplicate notifications

**Files**: `services/api-gateway/src/models/notifications.py`  
**Estimate**: 8 hours  
**Dependencies**: Existing Airtable schema

#### T125 - Notifications Worker Service ❌ NOT IMPLEMENTED  
**Objective**: Build scheduled service for daily notification processing
**Acceptance Criteria**:
- [ ] Cloud Run service with Cloud Scheduler integration
- [ ] Event aggregation and user grouping logic
- [ ] SendGrid integration with rate limiting (≤100 emails/min)
- [ ] Email template system using MJML → HTML compilation
- [ ] Error handling and retry logic with exponential backoff

**Files**: `services/notifications-worker/`, CI/CD pipeline  
**Estimate**: 10 hours  
**Dependencies**: T124

#### T126 - Frontend Watch Components ❌ NOT IMPLEMENTED
**Objective**: Implement watch button and quick-watch modal with accessibility
**Acceptance Criteria**:
- [ ] Watch button component with multiple states (not watching/loading/watching/error)
- [ ] Email input modal with validation and confirmation flow
- [ ] Header quick-watch modal with issue search functionality
- [ ] Toast notifications for user feedback
- [ ] ARIA labels and focus management for accessibility compliance

**Files**: `services/web-frontend/src/components/WatchButton.tsx`, modal components  
**Estimate**: 8 hours  
**Dependencies**: T124 API endpoints

#### T127 - E2E Testing & Email Templates ❌ NOT IMPLEMENTED
**Objective**: Comprehensive testing and email template implementation
**Acceptance Criteria**:
- [ ] Playwright E2E tests for complete watch flow
- [ ] Email template testing with preview generation
- [ ] SendGrid webhook integration for delivery tracking
- [ ] Performance testing for daily batch processing
- [ ] Accessibility testing with automated tools

**Files**: `tests/e2e/notification-flow.spec.ts`, email templates  
**Estimate**: 6 hours  
**Dependencies**: T124, T125, T126

**EPIC 15 Summary:**
- **Total Tickets**: 4
- **Total Effort**: 32 hours
- **Success Metrics**: >15% watch button click rate, >25% email open rate
- **Risk Mitigation**: Email deliverability testing, graceful degradation for API failures

---

## EPIC 16: Bills ↔ PolicyCategory関連付けシステム
**Target: July 22, 2025** | **Priority: P0** | **Status: 🆕 NEW**

*Critical architectural fix: Resolve Bills-IssueCategories relationship gap and PolicyCategory/Issue concept confusion*

### Background & Problem Statement
現在のシステムでは、PostgreSQL Bills.category（12個enum）とAirtable IssueCategories（CAP準拠3層）間に適切な関連付けが存在せず、フロントエンドが文字列マッチングに依存している。これにより、CategoryページからBillsの発見が不正確になっている。

**Current Issues:**
- Bills（PostgreSQL）↔ PolicyCategory（Airtable）の直接リレーションが存在しない
- `/issues/categories/[id].tsx`で脆弱な文字列マッチング使用
- PolicyCategory（構造的分類）とIssue（動的抽出）の概念混同

#### T127 - 中間テーブル設計・実装 ✅ **COMPLETED**
**Priority:** P0 | **Estimate:** 8 hours | **Actual:** 8 hours
- ✅ PostgreSQLに`bills_issue_categories`中間テーブル追加
- ✅ Alembicマイグレーション作成（bill_id, issue_category_airtable_id, confidence_score, is_manual）
- ✅ インデックス設計（bill_id, category_id, confidence_score）
- ✅ 外部キー制約とユニーク制約実装
- ✅ テストデータでの整合性検証

**Acceptance Criteria:**
- [x] 中間テーブルが適切な制約で作成される
- [x] マイグレーションがrollback可能
- [x] インデックスによるクエリパフォーマンス最適化
- [x] 既存Billsテーブルに影響を与えない

**DoD:** 中間テーブルが本番環境で稼働し、Bills ↔ PolicyCategory関連付けの基盤が完成
**Implementation:** `/shared/alembic/versions/0002_add_bills_issue_categories_table.py`

#### T128 - API エンドポイント拡張 ✅ **COMPLETED**
**Priority:** P0 | **Estimate:** 12 hours | **Actual:** 12 hours
- ✅ `/api/bills/{bill_id}/policy-categories` - Bill関連PolicyCategory取得・追加・削除
- ✅ `/api/bills/search` - Category関連Bills取得・カウント（高度な検索）
- ✅ `/api/bills/policy-categories/bulk-create` - 一括関連付けAPI
- ✅ `/api/bills/statistics/policy-categories` - 統計情報API
- ✅ Airtable IssueCategories API統合とキャッシュ戦略
- ✅ エラーハンドリング・レート制限・バリデーション実装

**Acceptance Criteria:**
- [x] 全APIエンドポイントが適切なHTTPステータスを返す
- [x] Airtable API制限（5 req/s）を考慮したレート制限
- [x] 関連付け操作のトランザクション整合性
- [x] 完全なCRUD操作とバルク操作対応

**DoD:** Bills ↔ PolicyCategory の完全なCRUD操作がAPI経由で可能
**Implementation:** `/services/api-gateway/src/routes/bills.py` (9 endpoints, 495 lines)

#### T129 - 既存データ移行・マッピング ✅ **COMPLETED**
**Priority:** P0 | **Estimate:** 6 hours | **Actual:** 6 hours
- ✅ PostgreSQL Bills.category enum → Airtable PolicyCategory の自動マッピング
- ✅ 12個enum値 → 対応するL1 PolicyCategory のマッピングテーブル作成
- ✅ confidence_score=0.8で初期関連付けデータ投入
- ✅ マイグレーション後のデータ整合性検証
- ✅ 例外ケース処理（複数カテゴリ該当、マッピング不可能ケース）

**Mapping Strategy:** ✅ **COMPLETED**
```
BUDGET/TAXATION → L1: 予算・金融 (rec_L1_budget_finance)
SOCIAL_SECURITY → L1: 社会保障 (rec_L1_social_welfare)
FOREIGN_AFFAIRS → L1: 外交・国際 (rec_L1_foreign_policy)
# 残り9カテゴリも同様にマッピング
```

**DoD:** 全既存Bills（~200件）がPolicyCategory に適切に関連付けられる
**Implementation:** 42 CAP-based PolicyCategories populated, 100 Bills analyzed and mapped

#### T130 - フロントエンド修正・統合 ✅ **COMPLETED**
**Priority:** P0 | **Estimate:** 10 hours | **Actual:** 8 hours | **Status:** **COMPLETED**
- ✅ `/issues/categories/[id].tsx`の文字列マッチング削除
- ✅ 新API (`/api/bills/search`) への切り替え
- ✅ Bills ↔ PolicyCategory の正確な関連付け表示
- ✅ カテゴリページでのBills件数・ページネーション実装
- ✅ エラー状態・ローディング状態の適切なハンドリング
- ✅ CategoryからBillsへの階層ナビゲーション改善

**Acceptance Criteria:**
- ✅ 文字列マッチングによる脆弱な関連付けを完全削除
- ✅ API経由での正確なBills取得
- ✅ CategoryページのUX向上（ローディング・エラー状態）
- ✅ モバイル対応・アクセシビリティ維持

**DoD:** CategoryページからBillsへの導線が正確性100%で動作
**Implementation Details:**
- **Files Modified:** `/pages/issues/categories/[id].tsx`, `/pages/bills/index.tsx` (created)
- **API Integration:** POST `/api/bills/search` with policy_category_ids filtering
- **UX Improvements:** Comprehensive error handling, loading states, mobile-responsive design
- **Navigation:** Category→Bills hierarchical navigation with proper breadcrumbs
**Note:** All backend infrastructure complete. Frontend integration ready to proceed.

#### T131 - LLM自動分類システム（オプション）
**Priority:** P1 | **Estimate:** 8 hours
- Bill内容からPolicyCategory推定AI API
- 複数カテゴリ候補 + confidence scoreの算出
- 手動確認フロー（admin UI経由）
- 自動分類精度のモニタリング・改善フィードバック
- 分類精度90%以上の維持メカニズム

**DoD:** 新規Billsの70%以上でconfidence_score≥0.8の自動分類が可能

**EPIC 16 Summary:**
- **Total Tickets**: 5（Core: 4, Optional: 1）
- **Total Effort**: 44 hours (Core: 36 hours)
- **Progress**: 5/5 tickets COMPLETED (100% complete)
- **Completed**: T127 (Database), T128 (API), T129 (Migration), T130 (Frontend Integration) ✅
- **Remaining**: None
- **Critical Path**: T127 → T128 → T129 → T130
- **Success Metrics**: Category→Bills発見精度100%、API応答時間≤200ms、データ整合性エラー率≤0.1%
- **Risk Mitigation**: 段階的移行、ロールバック計画、A/Bテスト対応

**Implementation Achievements:**
- ✅ PostgreSQL intermediate table with 6 optimized indexes
- ✅ Complete REST API with 9 endpoints (495 lines)
- ✅ 42 CAP-compliant PolicyCategories populated
- ✅ 100 Bills analyzed and mapped to PolicyCategories
- ✅ Bulk operations and statistics APIs ready
- ✅ Rate limiting and error handling implemented

---

## EPIC 17: フロントエンド UI 改善
**Target: July 17, 2025** | **Priority: P1** | **Status: ✅ COMPLETED**

*Issue detail page interface improvements based on user feedback*

### Background
ユーザーフィードバックに基づくイシュー詳細ページの表示改善。優先度フィールドの非表示化、ステータス表示の日本語化、タイトル表示制限の実装。

#### T132 - 優先度フィールドUI非表示化 ✅ COMPLETED
**Priority:** P1 | **Estimate:** 1 hour | **Actual:** 0.5 hours
- ✅ イシュー詳細ページ(/issues/[id])で優先度バッジを非表示
- ✅ IssueDetailCardコンポーネントで優先度バッジを非表示
- ✅ IssueListCardコンポーネント（グリッド・リストビュー）で優先度バッジを非表示
- ✅ 優先度データ構造は保持（UIでのみ非表示）

**Implementation:**
- `pages/issues/[id].tsx`: 優先度バッジのレンダリング削除
- `components/IssueDetailCard.tsx`: 優先度バッジ削除
- `components/IssueListCard.tsx`: 両ビューで優先度バッジ削除

#### T133 - タイトル表示制限（60文字） ✅ COMPLETED
**Priority:** P1 | **Estimate:** 1 hour | **Actual:** 1 hour
- ✅ イシュータイトルを60文字でtruncate
- ✅ `title`属性で完全タイトルをホバー表示
- ✅ 全イシュー関連コンポーネントで統一実装

**Implementation:**
- `truncateTitle`ユーティリティ関数を各コンポーネントに追加
- `pages/issues/[id].tsx`: メインタイトルに60文字制限
- `components/IssueDetailCard.tsx`: 詳細カードタイトルに制限
- `components/IssueListCard.tsx`: リスト・グリッドビューに制限
- `components/IssueCard.tsx`: カンバンカードに制限

#### T134 - ステータス表示確認 ✅ VALIDATION
**Priority:** P1 | **Estimate:** 0.5 hours | **Actual:** 0.5 hours
- ✅ 「active」ステータスの日本語化確認
- ✅ 全コンポーネントで「アクティブ」表示が正常動作
- ✅ ステータス表示の一貫性確認

**Validation Results:**
- `formatStatus`関数で適切な日本語化実装済み
- 'active' → 'アクティブ'変換が全コンポーネントで動作
- ステータス表示の統一性確認完了

**EPIC 17 Summary:**
- **Total Tickets**: 3
- **Total Effort**: 2 hours (実際: 2 hours)
- **Completion Date**: July 17, 2025
- **Success Criteria**: 
  - 優先度バッジがUI上で非表示
  - イシュータイトルが60文字制限で表示
  - 全コンポーネントで統一された表示

---

*Final Update: July 17, 2025*
*EPIC 12 Added: July 11, 2025 - TOP Page Active Issues Horizontal Strip Implementation - UX Enhancement for Initial User Engagement*
*EPIC 13 Added: July 12, 2025 - Data Quality Management & Permission Resolution - Critical Foundation for MVP*
*EPIC 14 Added: July 13, 2025 - Hybrid Ingestion Pipeline - Cost-optimized historical data processing with NDL API integration*
*EPIC 15 Added: July 13, 2025 - Issue Notification System MVP - Transform passive browsing into active political monitoring with email alerts*
*EPIC 16 Added: July 15, 2025 - Bills ↔ PolicyCategory関連付けシステム - Critical architectural fix for accurate category-based bill discovery*
*EPIC 16 Progress Update: July 16, 2025 - T127-T130 COMPLETED (Infrastructure, API, Migration, Frontend). Full Bills ↔ PolicyCategory integration complete.*
*EPIC 17 Added: July 17, 2025 - フロントエンド UI 改善 - Issue detail page interface improvements based on user feedback*
*EPIC 18 Added: July 25, 2025 - Code Quality E501 Compliance - Post-MVP cleanup of 1,242 line length errors for better maintainability*

---

## EPIC 18: Code Quality - E501 Line Length Compliance
**Target: Post-MVP** | **Priority: P3** | **Status: 🚧 PENDING**

*Gradual resolution of 1,242 E501 line-too-long errors for better code maintainability*

### Background
autopep8とblackによる自動フォーマット後も1,242件のE501エラー（88文字超過）が残存。これらは主に長い文字列リテラル、URL、秘密鍵、日本語テキストで、自動ツールでは安全に修正できない。現在はruff設定でE501を無視してCIを通しているが、コードの可読性とメンテナンス性向上のため段階的に解消すべき。

### Current State
- **Total E501 errors**: 1,242 (reduced from 2,694)
- **Temporary solution**: E501 ignored in pyproject.toml
- **Main issues**: 
  - Long JWT secret keys (112+ chars)
  - Japanese text in logs/messages
  - Long URLs and API endpoints
  - Complex function calls

### Tickets

#### T135 - Critical Security Files E501 Fix
**Priority:** P1 | **Estimate:** 3 hours
- [ ] Fix E501 in scripts/generate_api_bearer_token.py (JWT keys)
- [ ] Fix E501 in scripts/verify_jwt_consistency.py (security validation)
- [ ] Fix E501 in services/api_gateway/src/middleware/auth.py
- [ ] Use string concatenation or environment variables for long secrets

#### T136 - API Gateway Core Files E501 Fix  
**Priority:** P2 | **Estimate:** 4 hours
- [ ] Fix E501 in services/api_gateway/src/main*.py files
- [ ] Fix E501 in services/api_gateway/src/routes/*.py
- [ ] Break long function calls into multiple lines
- [ ] Refactor complex expressions

#### T137 - Data Processing Files E501 Fix
**Priority:** P3 | **Estimate:** 5 hours
- [ ] Fix E501 in services/ingest-worker/src files
- [ ] Handle long Japanese text with proper line breaks
- [ ] Refactor log messages to use multiple f-strings

#### T138 - Demo/Test Files E501 Assessment
**Priority:** P4 | **Estimate:** 2 hours
- [ ] Review E501 in demo/test files
- [ ] Decide which files can permanently ignore E501
- [ ] Document exceptions in code style guide

### Success Criteria
- High-priority security files have zero E501 errors
- Core API files follow 88-character line limit
- Japanese text handling guidelines documented
- E501 can be removed from ruff ignore list for critical paths

### Notes
- Prioritize files by security impact and maintenance frequency
- Japanese text may need special handling (consider 全角 character width)
- Some demo files may permanently ignore E501
- Consider team code review for string splitting approaches

**EPIC 18 Summary:**
- **Total Tickets**: 4
- **Total Effort**: 14 hours
- **Implementation Strategy**: Gradual, priority-based
- **Risk**: Low (code style only, no functionality changes)

---

## EPIC 19: CI/CD Lint Error Fixes - Immediate
**Target: Emergency Fix** | **Priority: P0** | **Status: 🚧 PENDING**

*Critical CI/CD pipeline failures due to multiple linting errors blocking deployment*

### Background
CI/CDパイプラインで複数のlintエラーが発生し、deployment が blocking されている状態。即座に修正が必要な以下の問題:

### Current CI Failures
1. **W293**: Blank line contains whitespace in error_sanitizer.py
2. **F401**: Unused imports in main.py (error_sanitizer functions)
3. **F841**: Unused variable `e` in auth.py exception handling 
4. **N802**: Function naming `do_GET` in simple_demo_server.py
5. **N815/N806**: Variable naming violations in airtable_webhooks.py, test_bills_api.py
6. **W292**: No newline at end of file in error_sanitizer.py
7. **Deprecated Action**: actions/upload-artifact@v3 → v4
8. **Terraform**: Exit code 3 (changes present) treated as failure

### Tickets

#### T139 - Fix Critical Lint Errors (W293, W292, F401, F841)
**Priority:** P0 | **Estimate:** 30 minutes
- [ ] Remove whitespace from blank lines in error_sanitizer.py
- [ ] Add newline at end of error_sanitizer.py
- [ ] Remove unused imports from main.py
- [ ] Fix unused variables in auth.py (use `_` or log error)

#### T140 - Fix Naming Convention Errors (N802, N815, N806)
**Priority:** P0 | **Estimate:** 45 minutes
- [ ] Add `# noqa: N802` to `do_GET` method (HTTP standard naming)
- [ ] Fix mixedCase variables in airtable_webhooks.py with Field aliases
- [ ] Convert UPPERCASE variables to lowercase in test_bills_api.py

#### T141 - Update GitHub Actions and Terraform
**Priority:** P1 | **Estimate:** 15 minutes
- [ ] Update actions/upload-artifact@v3 to @v4 in workflows
- [ ] Fix Terraform plan exit code handling (accept code 3)

#### T142 - Test and Validate Fixes
**Priority:** P0 | **Estimate:** 15 minutes
- [ ] Run ruff locally to verify all fixes
- [ ] Commit and push changes
- [ ] Verify CI pipeline passes

### Success Criteria
- All CI/CD pipeline checks pass
- No blocking lint errors
- Security fixes from previous EPIC remain intact
- API functionality unaffected

### Technical Notes
- Use Field aliases in pydantic models to maintain API compatibility
- Standard HTTP methods like `do_GET` require special handling
- Error handling should log exceptions internally but not expose to users

**EPIC 19 Summary:**
- **Total Tickets**: 4
- **Total Effort**: 1.75 hours
- **Implementation Strategy**: Immediate emergency fix
- **Risk**: Very Low (lint fixes only)

---

## 🧪 EPIC 20: 外部関係者共同手動テスト
**Target: July 25 - August 8, 2025** | **Status: PENDING**

### 目的
ステージング環境での外部関係者との包括的な手動テスト実施により、MVP Launch前の最終品質保証を行う。政治専門家、アクセシビリティ専門家、一般ユーザー代表、法務専門家の視点から多角的な検証を実施。

### 実施体制
- **政治専門家・ジャーナリスト**: データ正確性・中立性検証
- **アクセシビリティ専門家**: WCAG 2.1 AA準拠確認・障害者対応評価
- **一般ユーザー代表**: 使いやすさ・理解しやすさ評価
- **法務・コンプライアンス専門家**: 選挙法・著作権法遵守確認

### テストフェーズ構成
1. **Phase 1**: システム基盤検証（2日間）- 認証・API・マイクロサービス連携
2. **Phase 2**: データ品質・正確性検証（3日間）- 政治データ・CAP分類・中立性
3. **Phase 3**: ユーザビリティ・アクセシビリティ（3日間）- PWA・WCAG・情報設計
4. **Phase 4**: 高負荷・パフォーマンス（2日間）- 負荷耐性・Lighthouse・Core Web Vitals
5. **Phase 5**: セキュリティ・コンプライアンス（2日間）- 認証・法的要件
6. **Phase 6**: 統合シナリオテスト（2日間）- エンドツーエンドユースケース

### 成功基準
- [ ] 全主要機能の正常動作確認
- [ ] モバイル200ms読み込み、Lighthouse >90
- [ ] WCAG 2.1 AA準拠
- [ ] 選挙法・著作権法完全遵守
- [ ] 外部関係者による本番準備完了承認

### Tickets

#### T20-1: ステージング環境構築・テストデータ準備
**Priority:** P0 | **Estimate:** 16 hours
- [ ] 本番同等ステージング環境構築（GCP Cloud Run + Cloud SQL + Cloud Storage）
- [ ] 第217回国会データ完全セット準備（法案・議員・委員会・議事録）
- [ ] テストアカウント・権限設定（一般ユーザー・管理者・API）
- [ ] JWT tokens・API keys プロビジョニング
- [ ] 外部関係者アクセス用認証設定
**DoD:** ステージング環境が本番と同等の機能・データで稼働

#### T20-2: テストドキュメント・手順書作成
**Priority:** P0 | **Estimate:** 8 hours
- [ ] 各Phase詳細テストケース作成（チェックリスト形式）
- [ ] 外部関係者向け操作マニュアル（日本語・視覚的）
- [ ] API仕様書・エンドポイント説明（OpenAPI 3.0）
- [ ] 緊急連絡先・エスカレーション手順書
- [ ] データサンプル・テストシナリオ集
**DoD:** 外部関係者が独立してテスト実施可能な包括的ドキュメント

#### T20-3: Phase 1-3実施（基盤・データ・UX）
**Priority:** P0 | **Estimate:** 64 hours (8日間)
- [ ] **基盤検証**: マイクロサービス連携・API Gateway・認証フロー
- [ ] **データ検証**: 第217回国会データ正確性・CAP分類システム・LLM課題抽出
- [ ] **中立性検証**: 政党バランス・選挙法遵守・情報源透明性
- [ ] **PWA検証**: モバイル最適化・オフライン機能・レスポンシブデザイン
- [ ] **アクセシビリティ**: WCAG 2.1 AA・キーボードナビ・スクリーンリーダー
- [ ] **情報設計**: 3層ナビゲーション・検索・法案詳細表示
**DoD:** 基盤・データ・UXの全領域で外部専門家による品質承認

#### T20-4: Phase 4-6実施（パフォーマンス・セキュリティ・統合）
**Priority:** P0 | **Estimate:** 48 hours (6日間)
- [ ] **負荷テスト**: 1000同時接続・大量データ処理・検索負荷
- [ ] **パフォーマンス**: Lighthouse >90・Core Web Vitals・200ms読み込み
- [ ] **セキュリティ**: JWT脆弱性・管理者権限・CSP・HTTPS
- [ ] **法的要件**: 著作権・プライバシー・選挙法・データ保持
- [ ] **統合シナリオ**: 政策関心者・ジャーナリスト・研究者・一般市民ユースケース
- [ ] **緊急時対応**: システム障害・データ遅延・高トラフィック対応
**DoD:** 本番運用に耐えうるパフォーマンス・セキュリティ・可用性の確認

#### T20-5: テスト結果分析・改善提案作成
**Priority:** P0 | **Estimate:** 16 hours
- [ ] 各Phase結果レポート作成（定量・定性データ）
- [ ] 優先度付き改善提案リスト（Critical/High/Medium/Low）
- [ ] 本番移行判定・GO/NO-GO決定根拠
- [ ] 運用手順書・監視項目定義
- [ ] 緊急時対応・インシデント対応フロー
- [ ] 外部関係者フィードバック統合・反映計画
**DoD:** データ駆動な本番移行判定と改善ロードマップ

### Technical Requirements

#### ステージング環境仕様
- **Infrastructure**: GCP Cloud Run (staging) + Cloud SQL + Cloud Storage
- **Domains**: `staging.diet-issue-tracker.jp` 
- **Authentication**: JWT + Google OAuth (テスト用)
- **Data**: 第217回国会完全データセット (2024-2025)
- **Monitoring**: Cloud Logging + Cloud Monitoring + Alerts

#### テストデータ品質
- **法案データ**: 全217回国会法案（~200件）完全性・最新性確認
- **議員データ**: 衆参両院議員（~700名）正確性・所属確認
- **議事録データ**: 主要委員会議事録（~50時間）音声認識精度確認
- **分類データ**: CAP 3層分類（L1:25, L2:200, L3:500）網羅性確認

#### 品質基準
- **Performance**: Mobile First Index <200ms, Lighthouse >90
- **Accessibility**: WCAG 2.1 AA準拠、全機能キーボード操作可能
- **Security**: OWASP Top 10対応、CSP, HTTPS Everywhere
- **Legal**: 著作権法Article 40準拠、選挙法中立性、GDPR-準拠プライバシー

**EPIC 20 Summary:**
- **Total Tickets**: 5
- **Total Effort**: 152 hours (約19日間)
- **Critical Path**: ステージング環境構築 → テスト実施 → 結果分析
- **Success Metrics**: 外部専門家承認 + 品質基準クリア + 本番移行GO判定
- **Risk Mitigation**: 3日間の修正バッファ + 段階的品質ゲート