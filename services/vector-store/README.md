# Vector Store Service

Embedding generation and semantic search service for the Diet Issue Tracker.

## Overview

This service provides:
- Text embedding generation using Japanese-optimized models
- Vector similarity search with pgvector
- Semantic analysis of bills and debates
- Topic clustering and discovery

## Tech Stack

- Python 3.11+
- PostgreSQL with pgvector extension
- sentence-transformers (multilingual-E5)
- OpenAI embeddings (text-embedding-3-large)

## Directory Structure

```
vector-store/
├── src/
│   ├── embeddings/     # Vector generation clients
│   └── search/         # Search and filtering logic
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── scripts/            # Utility scripts
```

## Configuration

See `pyproject.toml` for dependencies and configuration.

## Development

```bash
# Install dependencies
python3 -m pip install -e .

# Run tests
python3 -m pytest

# Run linting
ruff check .
ruff format .
```