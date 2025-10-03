# Multi-Source Scraper Architecture

## Overview

This scraper uses a **modular architecture** that allows scraping from multiple Indonesian regulation databases with shared components and source-specific implementations.

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│       main_unified.py (CLI)             │
│  ┌───────────────────────────────────┐  │
│  │  Source Selection & Configuration │  │
│  └───────────────────────────────────┘  │
└──────────┬──────────────┬───────────────┘
           │              │
           ▼              ▼
    ┌──────────┐   ┌──────────┐
    │ peraturan│   │   BPK    │
    │  .go.id  │   │ Scraper  │
    │ Scraper  │   │          │
    └─────┬────┘   └────┬─────┘
          │             │
          └──────┬──────┘
                 │
                 ▼
        ┌────────────────┐
        │  BaseScraper   │
        │  (Abstract)    │
        └────────┬───────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Database │ │  Error  │ │ Session │
│ Manager │ │ Tracker │ │ Manager │
└─────────┘ └─────────┘ └─────────┘
```

## Component Details

### 1. Base Components (`src/core/`)

#### `base_scraper.py`
Abstract base class providing:
- Session management (thread-safe)
- Error tracking and logging
- State save/resume functionality
- Retry logic framework
- Abstract methods for subclass implementation

**Key Methods:**
- `get_session()` - Thread-safe session management
- `save_scraping_state()` - Save progress
- `load_scraping_state()` - Resume from save
- `cleanup()` - Resource cleanup

**Abstract Methods (must be implemented):**
- `get_total_pages()` - Get total pages to scrape
- `parse_page(page_num)` - Parse single page
- `scrape_all_with_validation()` - Main scraping logic

### 2. Source-Specific Scrapers (`src/scrapers/`)

#### `peraturan_go_id_scraper.py`
Wraps existing enhanced scraper for peraturan.go.id
- Extends `EnhancedPerdaScraper`
- Adds source tracking
- 985 pages × 20 items = ~19,686 records

#### `bpk_scraper.py` (NEW)
New scraper for peraturan.bpk.go.id
- Extends `BaseScraper`
- Card-based layout parsing
- 5,893 pages × 10 items = ~58,930 records
- More conservative rate limiting
- PDF download support with content-type validation
- PDFs saved to `docs/bpk/{year}/{region}/`

### 3. Configuration (`src/config/`)

Each source has its own config file:
- Base URLs and endpoints
- Scraping parameters (workers, delays, etc.)
- PDF download settings
- HTML selectors (for parsing)

### 4. Database (`src/database.py`)

Unified SQLite database with:
- `source` field to distinguish data sources
- Indexes on source, year, region
- Unique constraint on `detail_url`
- Shared schema for all sources

### 5. Entry Points

#### `main_unified.py` (NEW - Recommended)
Multi-source CLI supporting:
- Source selection (`--source peraturan|bpk|all`)
- Per-source configuration
- Preset modes (fast, stable, ultra)
- Parallel source execution

#### `main.py` (Legacy)
Single-source entry point for peraturan.go.id only
- Backward compatible
- Uses existing enhanced scraper

## Data Flow

```
1. User runs main_unified.py with --source selection
                 ↓
2. Create scraper instance(s) based on selection
                 ↓
3. Each scraper:
   a. Loads previous state (if exists)
   b. Determines pages to scrape
   c. Creates thread pool
   d. Scrapes pages concurrently
   e. Validates results
   f. Saves to unified database
   g. Logs activities/errors
   h. Saves state periodically
                 ↓
4. Report final statistics
```

## Database Schema

```sql
CREATE TABLE perda (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,              -- 'peraturan_go_id' or 'bpk'
    title TEXT NOT NULL,
    number TEXT,
    year INTEGER,
    region_name TEXT,
    region_type TEXT,
    detail_url TEXT UNIQUE,
    pdf_url TEXT,
    pdf_path TEXT,
    description TEXT,
    status TEXT,
    metadata JSON,
    scraped_at TIMESTAMP
);

CREATE INDEX idx_perda_source ON perda(source);
CREATE INDEX idx_perda_year ON perda(year);
CREATE INDEX idx_perda_region ON perda(region_name);
```

## Logging Strategy

Each source has separate log files:

```
logs/
├── peraturan_go_id_activity.log   # All activities for peraturan.go.id
├── peraturan_go_id_errors.log     # Errors for peraturan.go.id
├── bpk_activity.log               # All activities for BPK
└── bpk_errors.log                 # Errors for BPK
```

**Log Levels:**
- INFO: Normal operations, page completions
- WARNING: Retries, low item counts
- ERROR: Failed pages, exceptions

## State Management

Each source maintains its own state file:

```json
// scraping_state_peraturan_go_id.json
{
  "scraped_pages": [1, 2, 3, ...],
  "failed_pages": {
    "45": "Connection timeout"
  },
  "total_items": 15234,
  "timestamp": "2025-09-30T10:30:00"
}
```

Allows independent resume for each source.

## Adding New Sources

### Step-by-Step Guide

1. **Create Configuration** (`src/config/new_source_config.py`)
```python
SOURCE_NAME = "new_source"
BASE_URL = "https://example.com"
DEFAULT_WORKERS = 10
# ... other settings
```

2. **Create Scraper** (`src/scrapers/new_source_scraper.py`)
```python
from src.core.base_scraper import BaseScraper
from config.new_source_config import *

class NewSourceScraper(BaseScraper):
    def __init__(self, **kwargs):
        super().__init__(
            source_name=SOURCE_NAME,
            base_url=BASE_URL,
            **kwargs
        )

    def get_total_pages(self) -> int:
        # Implement page counting logic
        pass

    def parse_page(self, page_num: int) -> list:
        # Implement page parsing logic
        pass

    def scrape_all_with_validation(self):
        # Implement main scraping logic
        pass

def create_scraper(**kwargs):
    return NewSourceScraper(**kwargs)
```

3. **Update main_unified.py**
```python
from scrapers.new_source_scraper import create_scraper as create_new_scraper

# Add to source selection
if args.source in ['new_source', 'all']:
    scrapers_to_run.append(('New Source', create_new_scraper, config))
```

4. **Test Independently**
```bash
python main_unified.py --source new_source --workers 2 --min-items 5
```

## Performance Tuning

### peraturan.go.id
- **Fast**: 40 workers, 2-3s per page
- **Stable**: 15 workers, more reliable
- **Ultra**: 50 workers (risky, test first)

### BPK (peraturan.bpk.go.id)
- **Fast**: 15 workers (recommended max)
- **Stable**: 5 workers (very safe)
- Delays: 2-4 seconds (conservative)
- Government site = respect rate limits!

## Error Handling

### Retry Strategy
1. Request fails → Wait 2-5s → Retry
2. Low items → Wait longer → Retry
3. After max retries → Log as failed
4. Continue with next page

### Error Types Tracked
- `timeout`: Request timeouts
- `rate_limit`: Rate limiting detected
- `parse_error`: HTML parsing issues
- `low_items`: Page validation failed
- `connection`: Network errors

## Best Practices

1. **Always start with stable mode** for new sources
2. **Monitor logs** in real-time during first run
3. **Test with small batch** (3-5 workers) first
4. **Respect rate limits** - government sites are sensitive
5. **Use state files** - resume instead of restart
6. **Check database** regularly for duplicates
7. **Backup database** before large scraping runs

## Troubleshooting

### High Failure Rate
```bash
# Reduce workers
python main_unified.py --source bpk --workers 3 --stable
```

### Memory Issues
```bash
# Disable PDFs
python main_unified.py --source bpk --no-pdf
```

### Rate Limiting
```bash
# Use stable mode with fewer workers
python main_unified.py --source bpk --stable
```

### Check Progress
```bash
# Monitor logs
tail -f logs/bpk_activity.log

# Check database
sqlite3 database/perda.db "SELECT source, COUNT(*) FROM perda GROUP BY source;"
```

## Developed By

**Nuroji Lukman Syah**
- Email: dev@csis.or.id
- Open for contributions and modifications