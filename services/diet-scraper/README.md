# Diet Scraper Service

Data collection service for the Diet Issue Tracker that scrapes information from Japanese Diet websites.

## Overview

This service is responsible for:

- Scraping bill information from Diet websites
- Collecting transcript data (TXT/PDF)
- Processing Diet TV video links (HLS)
- Integration with National Diet Library Minutes API

## Tech Stack

- Python 3.11+
- requests + BeautifulSoup for HTML parsing
- Scrapy for complex scraping tasks
- Rate limiting and robots.txt compliance

## Directory Structure

```
diet-scraper/
├── src/
│   ├── collectors/       # API clients (NDL API, etc.)
│   └── scraper/         # Web scraping modules
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
