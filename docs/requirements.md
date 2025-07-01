# Diet Issue Tracker - Requirements Specification

## 1. Project Overview

### 1.1 Purpose
Independent, open-source platform for tracking Japanese Diet (parliament) issues as structured tickets with AI-powered analysis capabilities.

### 1.2 Scope
- Real-time data collection from Diet websites and proceedings
- Speech-to-text processing of parliamentary debates
- AI-powered content analysis and issue extraction
- Semantic search and recommendation system
- Public-facing web interface for citizen engagement

### 1.3 Key Constraints
- **Deadline**: MVP release before July 22, 2025 (House of Councillors election)
- **Legal Compliance**: Japanese election law, copyright law, privacy regulations
- **Neutrality**: Maintain political neutrality, no endorsements or donations

## 2. Functional Requirements

### 2.1 Data Collection (diet-scraper)
- **FR-001**: Collect bill data from Diet websites (sangiin.go.jp)
- **FR-002**: Extract bill metadata (ID, title, status, submitter, category)
- **FR-003**: Download parliamentary session transcripts (TXT/PDF)
- **FR-004**: Capture Diet TV video streams (HLS format)
- **FR-005**: Implement rate limiting (1-2 second delays, respect robots.txt)
- **FR-006**: Handle errors with exponential backoff retry logic

### 2.2 Speech Processing (stt-worker)
- **FR-007**: Convert audio/video to text using OpenAI Whisper large-v3
- **FR-008**: Achieve Word Error Rate (WER) ≤ 15% for Japanese speech
- **FR-009**: Process audio files asynchronously via message queue
- **FR-010**: Store raw audio in Cloud Storage, transcripts in PostgreSQL

### 2.3 Data Processing & AI Analysis (data-processor)
- **FR-011**: Extract entities: {Issue, Bill, Stage, Party, Member, Vote}
- **FR-012**: Categorize bills: 予算・決算, 税制, 社会保障, 外交・国際, 経済・産業, その他
- **FR-013**: Track bill workflow: Backlog → 審議中 → 採決待ち → 成立
- **FR-014**: **[NEW]** Dynamic issue extraction from bill content using LLM
- **FR-015**: **[NEW]** Parliamentary debate content analysis and topic modeling
- **FR-016**: **[NEW]** Automatic bill-to-debate content linking via semantic similarity
- **FR-017**: **[NEW]** Current political issue trend analysis from aggregated content
- **FR-018**: **[NEW]** Bill social impact assessment using multi-factor LLM evaluation
- **FR-019**: **[NEW]** Cross-reference analysis between related bills and policy discussions
- **FR-020**: **[NEW]** Temporal tracking of political agenda shifts and emerging issues

### 2.4 Vector Search & Semantic Analysis (vector-store)
- **FR-021**: Generate embeddings using Japanese-optimized models
- **FR-022**: Implement vector similarity search with pgvector
- **FR-023**: Support incremental indexing for new content
- **FR-024**: **[NEW]** Semantic similarity search between bills and debates
- **FR-025**: **[NEW]** Issue-based clustering and topic discovery
- **FR-026**: **[NEW]** Cross-temporal policy evolution tracking
- **FR-027**: **[NEW]** Similar bill recommendation system
- **FR-028**: **[NEW]** Political stance analysis through embedding space geometry

### 2.5 API Gateway (api-gateway)
- **FR-029**: Provide unified REST API with OpenAPI 3.0 specifications
- **FR-030**: Implement JWT-based authentication
- **FR-031**: Rate limiting per user and per endpoint
- **FR-032**: CORS configuration for frontend domains
- **FR-033**: API versioning and backward compatibility

### 2.6 Web Frontend (web-frontend)
- **FR-034**: Progressive Web App (PWA) with offline capabilities
- **FR-035**: Mobile-first responsive design
- **FR-036**: Accessibility features (ARIA labels, keyboard navigation)
- **FR-037**: Color-blind friendly palette (#27AE60/#C0392B/#F1C40F)
- **FR-038**: Furigana toggle for Japanese text readability
- **FR-039**: **[NEW]** Issue trend dashboard with LLM-generated insights
- **FR-040**: **[NEW]** Bill impact visualization and analysis summaries
- **FR-041**: **[NEW]** Semantic search interface for bill and debate content
- **FR-042**: **[NEW]** Personalized bill recommendations based on user interests  
- **FR-043**: **[NEW]** Real-time political agenda tracking and alerts

## 3. Non-Functional Requirements

### 3.1 Performance
- **NFR-001**: Mobile page load time ≤ 200ms
- **NFR-002**: API response time p95 ≤ 500ms
- **NFR-003**: Support 1000+ concurrent users
- **NFR-004**: Lighthouse performance score > 90

### 3.2 Availability & Reliability
- **NFR-005**: System uptime ≥ 99.5%
- **NFR-006**: Data backup with RPO ≤ 1 hour
- **NFR-007**: Disaster recovery with RTO ≤ 4 hours
- **NFR-008**: Graceful degradation during service failures

### 3.3 Scalability
- **NFR-009**: Horizontal scaling for all microservices
- **NFR-010**: Auto-scaling based on CPU/memory utilization
- **NFR-011**: Database read replicas for load distribution
- **NFR-012**: CDN for static asset delivery

### 3.4 Security
- **NFR-013**: HTTPS/TLS 1.3 for all communications
- **NFR-014**: Input validation and sanitization
- **NFR-015**: SQL injection and XSS protection
- **NFR-016**: Rate limiting to prevent DoS attacks
- **NFR-017**: No storage of secrets in code repositories

### 3.5 Usability & Accessibility
- **NFR-018**: WCAG 2.1 AA compliance
- **NFR-019**: Multi-device compatibility (mobile, tablet, desktop)
- **NFR-020**: Japanese language support with proper typography
- **NFR-021**: Intuitive navigation with ≤ 3 clicks to key information

## 4. Technical Requirements

### 4.1 Architecture
- **TR-001**: Microservices architecture with 6 core services
- **TR-002**: Event-driven communication via Cloud Pub/Sub
- **TR-003**: Container deployment with Docker
- **TR-004**: Infrastructure as Code (IaC) with Terraform

### 4.2 Technology Stack
- **TR-005**: Backend: Python 3.11.2 with FastAPI
- **TR-006**: Frontend: Next.js with TypeScript
- **TR-007**: Database: PostgreSQL with pgvector extension
- **TR-008**: Message Queue: Google Cloud Pub/Sub
- **TR-009**: Infrastructure: Google Cloud Platform (GCP)
- **TR-010**: AI/ML: OpenAI API, Claude API, Whisper, sentence-transformers

### 4.3 Data Storage
- **TR-011**: Structured data in PostgreSQL
- **TR-012**: Vector embeddings in pgvector
- **TR-013**: Binary files in Cloud Storage
- **TR-014**: Application logs in Cloud Logging
- **TR-015**: Metrics in Cloud Monitoring

### 4.4 Development & Deployment
- **TR-016**: Git version control with feature branches
- **TR-017**: Conventional Commits for commit messages
- **TR-018**: GitHub Actions for CI/CD pipeline
- **TR-019**: Blue-green deployment strategy
- **TR-020**: Automated testing (unit, integration, E2E)

## 5. Legal & Compliance Requirements

### 5.1 Copyright & Intellectual Property
- **LR-001**: Comply with Article 40 of Japanese Copyright Law for parliamentary speeches
- **LR-002**: Link to original video sources, avoid redistribution
- **LR-003**: Release source code under MIT license
- **LR-004**: Respect third-party library licenses

### 5.2 Privacy & Data Protection
- **LR-005**: Process only public figure information (Diet members)
- **LR-006**: No collection or storage of citizen personal data
- **LR-007**: Clear data retention policies for audio/transcript storage
- **LR-008**: Privacy policy and terms of service

### 5.3 Election Law Compliance
- **LR-009**: Maintain strict political neutrality
- **LR-010**: No candidate endorsements or political donations
- **LR-011**: Equal treatment of all political parties and positions
- **LR-012**: Transparent methodology for content analysis

## 6. Interface Requirements

### 6.1 External System Interfaces
- **IR-001**: Diet website APIs and HTML scraping interfaces
- **IR-002**: OpenAI API for LLM analysis and embeddings
- **IR-003**: Claude API for advanced content analysis
- **IR-004**: Google Cloud services APIs

### 6.2 User Interfaces
- **IR-005**: Web-based responsive UI for all device types
- **IR-006**: RESTful API for potential third-party integrations
- **IR-007**: Admin dashboard for system monitoring
- **IR-008**: Developer API documentation portal

### 6.3 Inter-Service Communication
- **IR-009**: Async messaging between microservices
- **IR-010**: OpenAPI specifications for all service interfaces
- **IR-011**: Service mesh for secure inter-service communication
- **IR-012**: Circuit breaker pattern for fault tolerance

## 7. Quality Attributes

### 7.1 Maintainability
- **QA-001**: Modular microservices architecture
- **QA-002**: Comprehensive documentation (code, API, deployment)
- **QA-003**: Consistent coding standards (PEP 8, ESLint)
- **QA-004**: Automated code quality checks (linting, type checking)

### 7.2 Testability
- **QA-005**: Unit test coverage ≥ 80%
- **QA-006**: Integration tests for all service interfaces
- **QA-007**: End-to-end tests for critical user journeys
- **QA-008**: Mock external dependencies for isolated testing

### 7.3 Observability
- **QA-009**: Structured JSON logging with correlation IDs
- **QA-010**: Metrics collection (latency, throughput, errors)
- **QA-011**: Distributed tracing for request flows
- **QA-012**: Alerting for SLO violations and system failures

## 8. Constraints & Assumptions

### 8.1 Technical Constraints
- **TC-001**: Japanese language processing requirements
- **TC-002**: Real-time data processing limitations
- **TC-003**: AI API rate limits and costs
- **TC-004**: GCP service availability and limitations

### 8.2 Business Constraints  
- **BC-001**: Limited budget for AI API usage
- **BC-002**: Single development team (human + AI agents)
- **BC-003**: Open source project with community contributions
- **BC-004**: Pre-election timeline pressure

### 8.3 Assumptions
- **AS-001**: Diet website structure remains stable
- **AS-002**: Sufficient quality of source audio/video for transcription
- **AS-003**: User acceptance of AI-generated analysis and summaries
- **AS-004**: Continued availability of third-party AI services

---

**Document Version**: 1.0  
**Last Updated**: 2025-06-30  
**Next Review**: 2025-07-07  
**Approved By**: [To be filled]

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-06-30 | Initial requirements specification with LLM analysis features | Claude |
