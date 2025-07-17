Diet Issue Tracker - Claude Code Memory

Project Overview
	•	Goal: Independent, open-source platform tracking Diet issues as tickets
	•	MVP Deadline: July 22, 2025 (House of Councillors election)
	•	Architecture: Microservices with human + AI agent collaboration
	•	Repository: Monorepo structure with services/, shared/, infra/, docs/, scripts/

Development Environment & Commands
	•	Python: Use python3 (version 3.11.2)
	•	Package Management: Install via python3 -m pip install package-name
	•	Testing: Run tests with python3 -m pytest in each service directory
	•	Linting: Use ruff check . and ruff format . for Python code
	•	Type Checking: Run mypy . in each service directory

Code Style & Standards
	•	Python: Follow PEP 8, use 4-space indentation
	•	Imports: Sort with isort, group stdlib/third-party/local
	•	Type Hints: Required for all function signatures
	•	Documentation: Use Google-style docstrings
	•	Error Handling: Explicit exception handling, avoid bare except
	•	Security: Never commit secrets, use environment variables

Architecture Decisions
	•	Microservices: 6 services (diet-scraper, stt-worker, data-processor, vector-store, api-gateway, web-frontend)
	•	Database: PostgreSQL with pgvector for embeddings
	•	Message Queue: Cloud Pub/Sub for inter-service communication
	•	API: RESTful APIs with OpenAPI 3.0 specifications
	•	Authentication: JWT tokens via api-gateway
	•	Infrastructure: GCP (Cloud Run, Cloud SQL, Cloud Storage)

### Notification Service (planned implementation)
	•	Scope: Issue progress alerts (bill stage change, committee meeting created)
	•	Trigger Sources:
	  • (A) bills.stage UPDATE (審議中→採決待ち/成立/否決)
	  • (B) meetings INSERT matching issue_id
	•	Delivery: Daily batch (22:00 JST) via SendGrid
	•	UX: Watch button on issue page & header quick-watch modal
	•	Implementation Status: NOT IMPLEMENTED (WatchButton.tsx contains only skeleton code)
	•	Future: (C) speech volume spike detection (Roadmap Phase 2)

Service-Specific Guidelines

diet-scraper
	•	Purpose: Data collection from Diet websites
	•	Tech Stack: Python + requests + BeautifulSoup + Scrapy
	•	Data Sources:
	  • Diet bill pages (HTML), transcripts (TXT/PDF), Diet TV (HLS)
	  • **National Diet Library Minutes API** for 第217回国会まで
	    • Scope: meetings ≤ 2025-06-21
	    • Rationale: STT コスト圧縮、メタ情報完備
	  • Whisper/STT for meetings ≥ 2025-06-22 (≤24 h latency)
	•	Rate Limiting: 
	  • (1) NDL Minutes API—JSON download, polite rate-limit (≤3 req/s)
	  • (2) Diet bill pages / transcripts / Diet TV (従来通り): 1-2 second delays, respect robots.txt
	•	Error Handling: Retry logic with exponential backoff
	•	Data Validation: WER ≤15% for speech recognition

stt-worker
	•	Purpose: Speech-to-text processing
	•	Tech Stack: Python + yt-dlp + OpenAI Whisper
	•	Model: Whisper large-v3 for Japanese
	•	Processing: Async job processing via message queue
	•	Storage: Raw audio in Cloud Storage, transcripts in PostgreSQL

data-processor
	•	Purpose: Data normalization, entity extraction, and LLM-based content analysis
	•	Tech Stack: Python + pandas + NLP libraries + OpenAI API/Claude API
	•	Entities: {Issue, Bill, Stage, Party, Member, Vote, IssueCategory}
	•	Workflow: Backlog → 審議中 → 採決待ち → 成立
	
	**Policy Classification Architecture** (CAP-based vs Issue-based):
	•	**PolicyCategory** (CAP準拠の構造的分類):
	  • L1 (Major Topics): ~25 categories (社会保障, 経済・産業, 外交・国際, etc.)
	  • L2 (Sub-Topics): ~200 categories (健康保険制度, 再生可能エネルギー, etc.)
	  • L3 (Specific Policy Areas): ~500 areas (高齢者医療, 太陽光発電, etc.)
	  • Purpose: International comparison, systematic classification
	  • Storage: Airtable IssueCategories table with hierarchical structure
	•	**Issue** (LLM駆動の動的抽出):
	  • Specific policy problems extracted from bills/debates (~500-1,000 items)
	  • Examples: "介護保険の自己負担率見直し", "カーボンニュートラル2050目標"
	  • Purpose: Current political agenda tracking, bill-to-debate linking
	  • Storage: Airtable Issues table with dynamic generation
	
	**Bills ↔ IssueCategories Relationship**:
	•	Current: PostgreSQL Bills.category (12 fixed enums) + Airtable IssueCategories (CAP-based)
	•	Required: Intermediate mapping table for Bills ↔ IssueCategories relationship
	•	Implementation: bills_issue_categories table with confidence scores and manual/auto flags
	
	•	CAP (Comparative Agendas Project) Integration: International policy classification standards
	•	Issue-first Information Architecture: Policy area → specific bills navigation
	•	LLM Analysis Features:
	•	Dynamic issue extraction from bill content using LLM
	•	Parliamentary debate content analysis and topic modeling
	•	Automatic bill-to-debate content linking based on semantic similarity
	•	Current political issue trend analysis from aggregated content
	•	Bill social impact assessment using multi-factor LLM evaluation
	•	Cross-reference analysis between related bills and policy discussions
	•	Temporal tracking of political agenda shifts and emerging issues

vector-store
	•	Purpose: Embedding generation, vector search, and semantic analysis
	•	Tech Stack: Python + pgvector + sentence-transformers + OpenAI embeddings
	•	Embeddings: Japanese-optimized models (multilingual-E5, OpenAI text-embedding-3-large)
	•	Indexing: Incremental updates for new content
	•	Advanced Search Features:
	•	Semantic similarity search between bills and debates
	•	Issue-based clustering and topic discovery
	•	Cross-temporal policy evolution tracking
	•	Similar bill recommendation system
	•	Political stance analysis through embedding space geometry

api-gateway
	•	Purpose: API integration, authentication, rate limiting
	•	Tech Stack: FastAPI + Redis + JWT
	•	CORS: Configure for frontend domain
	•	Rate Limiting: Per-user and per-endpoint limits
	•	3-Layer Issue Category APIs:
	•	/api/issues/categories - Hierarchical category management
	•	/api/issues/categories/tree - Full category tree retrieval
	•	/api/issues/categories/{id}/children - Child category queries
	•	Category-filtered search endpoints for bills and speeches

web-frontend
	•	Purpose: PWA frontend with accessibility focus and intelligent analysis features
	•	Tech Stack: Next.js + TypeScript + Tailwind CSS
	•	Design: Mobile-first, color-blind friendly palette (#27AE60/#C0392B/#F1C40F)
	•	Accessibility: ARIA labels, furigana toggle, keyboard navigation
	•	Performance: Mobile load ≤200ms, Lighthouse scores >90
	•	3-Layer Issue Navigation Features:
	•	/issues/categories - Category overview with drill-down navigation
	•	/issues/categories/{id} - Category detail pages with related bills
	•	Hierarchical breadcrumb navigation (L1 → L2 → Bills)
	•	Category-based filtering and search functionality
	•	Policy area statistics and trend visualization
	•	Intelligence Features:
	•	Issue trend dashboard with LLM-generated insights
	•	Bill impact visualization and analysis summaries
	•	Semantic search interface for bill and debate content
	•	Personalized bill recommendations based on user interests
	•	Real-time political agenda tracking and alerts

notifications-worker
	•	Purpose: Aggregate daily issue events & send emails  
	•	Tech Stack: Python + SendGrid SDK  
	•	Schedule: Cloud Scheduler → Cloud Run (`0 13 * * *` UTC)  
	•	Data:
	  • subscriptions(id, user_email, issue_id, confirmed_at, unsubscribed)  
	  • issue_events(id, issue_id, event_type, event_payload, happened_at)  
	•	Idempotency: fingerprint(event_type, payload) stored in issue_events  
	•	Rate Limit: ≤100 emails/min (SendGrid free tier safe)

Data & Legal Compliance
	•	Copyright: Speech under Article 40, link to videos, code under MIT
	•	Privacy: Minimal PII (only public figures), no personal data storage
	•	Election Law: Maintain neutrality, no endorsements, no donations
	•	Data Retention: Define clear policies for audio/transcript storage

Development Workflow
	•	Branching: Feature branches from main, PR required
	•	Commits: Conventional Commits format
	•	Reviews: Human review required for AI-generated code
	•	Testing: Unit tests + integration tests + E2E tests
	•	CI/CD: GitHub Actions with lint/test/accessibility gates
	•	Deployment: Blue-green deployment strategy

E2E Testing with Playwright MCP

Playwright MCP enables full-browser end-to-end tests that Claude can run or debug on demand.

Installation

claude mcp add -s user playwright npx @playwright/mcp@latest

Run this once per machine in the terminal (not in this file). It registers the server in user scope so every Claude Code session can invoke it.

Configuration

The root playwright.config.ts contains:

import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,           // set PWDEBUG=1 or use --headed for visual runs
  },
  webServer: {
    command: 'npm run dev',   // auto-start the dev server
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});

This lets Playwright (and Claude) spin up the local server automatically before tests.

Typical Claude prompts
	1.	Use playwright mcp to run all e2e tests
	2.	Use playwright mcp to open http://localhost:3000 in headed mode
	3.	Use playwright mcp to reproduce failing test tests/e2e/login.spec.ts:15

Running tests manually

npx playwright test --reporter=line          # run all specs
npx playwright show-report                   # open HTML report

Directory conventions
	•	Specs live in tests/e2e/**/*.spec.ts
	•	Screenshots/videos are saved to test-results/ by default

Debug workflow
	1.	Trigger a headed run: PWDEBUG=1 npx playwright test <file> or ask Claude with prompt #2 above.
	2.	Inspect the browser or use Playwright Inspector to step through.
	3.	Fix the issue, then rerun tests.

Note
This section documents usage only. The MCP server must already be installed with the command in Installation.

AI Agent Collaboration
	•	Service Assignment: One AI agent per microservice when possible
	•	API Contracts: Define OpenAPI specs before implementation
	•	Communication: Async messaging between services
	•	Testing: Mock external dependencies for isolated testing
	•	Documentation: Update this file when making architectural changes
	•	Web Research: When web research involves complex judgments or abstract questions, consult with o3 via MCP

o3 Consultation Best Practices & Rate Limit Management

When to Use o3
	•	Complex Technical Analysis: Deep debugging of unfamiliar error patterns
	•	Architecture Decisions: System design and technology stack choices
	•	Security Vulnerabilities: Advanced threat analysis and mitigation strategies
	•	Performance Optimization: Complex bottleneck analysis requiring domain expertise
	•	Standards Compliance: WCAG, security frameworks, coding standards interpretation

Rate Limit Avoidance Strategies

Current Limits: 30,000 TPM (Tokens Per Minute) - approximately 10-15 complex queries per minute
	1.	Batch Questions Efficiently:

❌ Bad: Multiple separate calls
- "What causes CORS 400 errors?"
- "How to fix FastAPI middleware order?"
- "Best practices for CORS headers?"

✅ Good: Single comprehensive query
- "FastAPI CORS preflight returning 400. I have CORSMiddleware configured but 
  preflight requests show '400 preflight' in DevTools. Current middleware stack: 
  [detailed config]. Browser shows: [specific errors]. What middleware order 
  issues or configuration problems could cause this?"


	2.	Strategic Timing:
	•	Wait 6-7 minutes between rate limit hits (shown in error message)
	•	Monitor token usage patterns during complex debugging sessions
	•	Use o3 for high-value questions where expertise gap is significant
	3.	Fallback Strategies:
	•	Use Gemini Flash (mcp__gemini__gemini_chat_flash) for simpler questions
	•	Leverage documentation search and Grep tools before escalating to o3
	•	Save o3 queries for situations requiring genuine reasoning/analysis
	4.	Query Optimization:
	•	Include relevant code snippets, error messages, and context in one message
	•	Ask for actionable solutions rather than general explanations
	•	Request prioritized recommendations when multiple approaches exist

Example Effective o3 Usage Pattern

Timeline: Complex CORS debugging session
00:00 - Initial analysis with local tools (Grep, Read, logs)
00:05 - First o3 query: Comprehensive problem description with full context
00:12 - Implement recommended solution
00:15 - Verify and test solution
00:20 - If issues persist: Second o3 query with update and new evidence

Key Principle: Treat o3 as a senior technical consultant - prepare thoroughly, ask precise questions, and implement recommendations before follow-up queries.

Troubleshooting
	•	Environment Issues: Use Docker for consistent development environment
	•	Database Issues: Check PostgreSQL connection and pgvector extension
	•	API Issues: Verify service health endpoints and logging
	•	Frontend Issues: Check console for JavaScript errors and network requests

Monitoring & Observability
	•	Logging: Structured JSON logs with Cloud Logging
	•	Metrics: Track p95 latency, error rates, data processing times
	•	Alerts: Set up for service failures and data pipeline issues
	•	SLOs: Define and monitor service level objectives

Quick References
	•	Diet Website: https://www.sangiin.go.jp/
	•	API Docs: Located in docs/api/ for each service
	•	Architecture Diagram: docs/architecture.md
	•	Deployment Guide: docs/deployment.md

⸻

Last updated: 2025-07-13
Added Playwright MCP E2E testing section
Added 3-Layer Issue Categorization System (CAP integration, hierarchical navigation)
Update this file when making significant changes to project structure or decisions