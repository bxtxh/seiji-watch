# Notifications Worker Service

Email notification service for the Diet Issue Tracker.

## Overview

This service handles:
- Daily batch email notifications (22:00 JST)
- Issue progress alerts (bill stage changes, committee meetings)
- SendGrid integration for email delivery
- Subscription management

## Tech Stack

- Python 3.11+
- SendGrid SDK
- Cloud Scheduler for cron jobs
- PostgreSQL for subscription data

## Directory Structure

```
notifications-worker/
├── src/
│   └── notifications/  # Notification logic
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── scripts/            # Utility scripts
```

## Database Schema

- `subscriptions`: User email subscriptions
- `issue_events`: Event tracking with idempotency

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