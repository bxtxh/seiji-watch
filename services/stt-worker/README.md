# STT Worker Service

Speech-to-text processing service for the Diet Issue Tracker.

## Overview

This service handles:
- Audio extraction from Diet TV streams using yt-dlp
- Speech-to-text conversion using OpenAI Whisper
- Async job processing via message queue
- Quality validation (WER ≤15%)

## Tech Stack

- Python 3.11+
- OpenAI Whisper (large-v3 model for Japanese)
- yt-dlp for audio extraction
- Cloud Pub/Sub for job queue

## Directory Structure

```
stt-worker/
├── src/
│   └── stt/            # Whisper client and processing
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