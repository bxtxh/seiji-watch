# Data Processor Service

Data normalization, entity extraction, and LLM-based content analysis service for the Diet Issue Tracker.

## Overview

This service handles:
- Data normalization from various Diet sources
- Entity extraction (Issues, Bills, Members, Parties, etc.)
- LLM-powered content analysis and classification
- Policy categorization using CAP standards
- Bill-to-debate content linking
- Political agenda trend analysis

## Tech Stack

- Python 3.11+
- pandas for data processing
- OpenAI API / Claude API for LLM analysis
- Airtable for dynamic data management
- PostgreSQL for structured data storage

## Core Features

### Policy Classification Architecture

1. **PolicyCategory** (CAP-based structural classification):
   - L1: ~25 major topics (社会保障, 経済・産業, 外交・国際, etc.)
   - L2: ~200 sub-topics (健康保険制度, 再生可能エネルギー, etc.)
   - L3: ~500 specific areas (高齢者医療, 太陽光発電, etc.)
   - Purpose: International comparison, systematic classification

2. **Issue** (LLM-driven dynamic extraction):
   - Specific policy problems extracted from bills/debates
   - Examples: "介護保険の自己負担率見直し", "カーボンニュートラル2050目標"
   - Purpose: Current political agenda tracking

### LLM Analysis Features

- Dynamic issue extraction from bill content
- Parliamentary debate content analysis
- Automatic bill-to-debate semantic linking
- Political issue trend analysis
- Bill social impact assessment
- Cross-reference analysis between related bills

## Directory Structure

```
data-processor/
├── src/
│   ├── processors/     # Data normalization modules
│   ├── extractors/     # Entity extraction logic
│   ├── analyzers/      # LLM analysis modules
│   ├── classifiers/    # Policy categorization
│   └── airtable/       # Airtable integration
├── scripts/            # Batch processing scripts
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── docs/               # Service documentation
```

## Data Flow

1. Raw data from diet-scraper and stt-worker
2. Normalization and validation
3. Entity extraction and relationship mapping
4. LLM analysis for content understanding
5. Policy categorization and issue tagging
6. Storage in PostgreSQL and Airtable

## Configuration

Environment variables:
- `DATABASE_URL` - PostgreSQL connection
- `AIRTABLE_API_KEY` - Airtable Personal Access Token
- `AIRTABLE_BASE_ID` - Airtable base identifier
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Claude API key

## Development

```bash
# Install dependencies
poetry install

# Run data processor
poetry run python -m src.main

# Run tests
poetry run pytest

# Run linting
ruff check .
ruff format .

# Type checking
poetry run mypy .
```

## Batch Scripts

Various utility scripts for data management:
- `bills_improvement_execution.py` - Bill data quality improvements
- `members_duplicate_merge_execution.py` - Member deduplication
- `table_completeness_improvement.py` - Data completeness checks
- `airtable_schema_inspector.py` - Airtable schema validation