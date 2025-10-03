# Multi-Source Perda Scraper

> **High-Performance Indonesian Regional Regulations Scraper**

A production-ready, modular scraper for Indonesian regional regulations (Peraturan Daerah) supporting **multiple data sources** with advanced retry logic, intelligent validation, and comprehensive error tracking.

**Developed by:** Nuroji Lukman Syah ([dev@csis.or.id](mailto:dev@csis.or.id))
*Feel free to modify and adapt this script for your needs*

## 📡 **Supported Sources**

1. **peraturan.go.id** - National regulation database (~985 pages, 20 items/page)
   - Full metadata and PDF download support
2. **peraturan.bpk.go.id** - BPK regulation database (~5,893 pages, 10 items/page)
   - Full metadata and PDF download support (when available)


## 🚀 Quick Start

### Using UV (Fastest)
```bash
# Install UV
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
# or: curl -LsSf https://astral.sh/uv/install.sh | sh       # macOS/Linux

# Install dependencies
uv pip install -r requirements.txt

# Scrape BOTH sources
uv run python main_unified.py --all

# Scrape only peraturan.go.id (existing source)
uv run python main_unified.py --source peraturan --fast

# Scrape only BPK (new source)
uv run python main_unified.py --source bpk --stable
```

### Using Standard Python
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Scrape both sources
python main_unified.py --all

# Scrape specific source
python main_unified.py --source peraturan --workers 30
python main_unified.py --source bpk --workers 10 --no-pdf
```

### Legacy Single-Source Mode
```bash
# Run original peraturan.go.id scraper only
python main.py --fast
```

## ✨ Key Features

- ✅ **Multi-Source Support**: Scrape from multiple Indonesian regulation databases
- ✅ **Modular Architecture**: Easy to add new data sources
- ✅ **Smart Retry Logic**: Automatically retries pages with insufficient items
- ✅ **Unified Database**: Single SQLite database with source tracking
- ✅ **Enhanced Logging**: Separate logs per source with detailed tracking
- ✅ **Error Recovery**: Comprehensive error tracking with suggested solutions
- ✅ **High Performance**: Configurable concurrent workers with intelligent rate limiting
- ✅ **PDF Downloads**: Organized download structure by source/year/region
- ✅ **State Management**: Save/resume scraping sessions per source
- ✅ **Flexible CLI**: Multiple preset configurations and source selection

## 📊 Recent Performance

Latest successful scraping session:
- **985 pages** scraped successfully (100% success rate)
- **17,301 records** stored in database
- **344 unique regions** across Indonesia
- **55 years** of data (1969-2024)
- **0 failed pages** with automatic retry

## 🛠 Installation

### Prerequisites
- Python 3.10 or higher
- pip (included with Python)
- Optional: [UV](https://github.com/astral-sh/uv) for faster dependency management

### Method 1: Using UV (Recommended - Faster)

UV is a fast Python package installer and resolver. It's significantly faster than pip and handles virtual environments automatically.

```bash
# Install UV (if not already installed)
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository>
cd scrapper

# Install dependencies (UV creates a virtual environment automatically)
uv pip install -r requirements.txt

# Run the scraper
uv run python main.py

# Or with options
uv run python main.py --fast
uv run python main.py --workers 20 --no-pdf
```

### Method 2: Using Standard Python (pip + venv)

```bash
# Clone the repository
git clone <repository>
cd scrapper

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the scraper
python main.py

# Or with options
python main.py --fast
python main.py --workers 20 --no-pdf
```

### Method 3: Quick Start (No Virtual Environment)

```bash
# Install dependencies globally (not recommended for production)
pip install -r requirements.txt

# Run the scraper
python main.py
```

### Verifying Installation

```bash
# Check Python version (should be 3.10+)
python --version

# Verify dependencies are installed
pip list | grep requests
pip list | grep beautifulsoup4

# Test run (lightweight test with 3 workers)
python main.py --workers 3 --min-items 10
```

## 📋 Usage

### Multi-Source Commands

```bash
# Scrape BOTH sources with default settings
python main_unified.py --all

# Scrape only peraturan.go.id
python main_unified.py --source peraturan --fast

# Scrape only BPK
python main_unified.py --source bpk --stable

# Custom configuration for specific source
python main_unified.py --source bpk --workers 5 --no-pdf --retries 3

# See all options
python main_unified.py --help
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--source` | Source to scrape: `peraturan`, `bpk`, or `all` | `all` |
| `--workers N` | Number of worker threads | Source-dependent |
| `--no-pdf` | Skip PDF downloads | False |
| `--retries N` | Max retries per page | 5 |
| `--min-items N` | Minimum items per page | Source-dependent |
| `--fast` | Fast preset (higher workers) | False |
| `--stable` | Stable preset (conservative) | False |
| `--ultra` | Ultra preset (peraturan.go.id only) | False |

### Source-Specific Defaults

| Setting | peraturan.go.id | peraturan.bpk.go.id |
|---------|-----------------|---------------------|
| Default Workers | 30 | 10 |
| Fast Workers | 40 | 15 |
| Stable Workers | 15 | 5 |
| Items/Page | 20 | 10 |
| Min Items | 18 | 8 |

## 📁 Project Structure

```
multi-source-perda-scraper/
├── main_unified.py                   # Multi-source CLI entry point
├── main.py                           # Legacy single-source entry point
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
│
├── src/
│   ├── core/                         # Shared components
│   │   ├── base_scraper.py          # Abstract base class
│   │   └── __init__.py
│   │
│   ├── scrapers/                     # Source-specific scrapers
│   │   ├── peraturan_go_id_scraper.py    # peraturan.go.id
│   │   ├── bpk_scraper.py                # peraturan.bpk.go.id
│   │   └── __init__.py
│   │
│   ├── config/                       # Configuration files
│   │   ├── peraturan_go_id_config.py     # peraturan.go.id config
│   │   ├── bpk_config.py                 # BPK config
│   │   └── __init__.py
│   │
│   ├── database.py                   # Unified database manager
│   ├── scraper_enhanced.py           # Legacy enhanced scraper
│   └── main.py                       # Legacy main module
│
├── database/
│   └── perda.db                      # Unified SQLite database
│
├── logs/                             # Source-specific logs
│   ├── peraturan_go_id_activity.log
│   ├── peraturan_go_id_errors.log
│   ├── bpk_activity.log
│   └── bpk_errors.log
│
├── docs/                             # PDFs organized by source
│   ├── peraturan_go_id/
│   │   └── {year}/{region}/
│   └── bpk/
│       └── {year}/{region}/
│
└── scraping_state_*.json             # State files per source
```

## 🔍 Monitoring & Logs

### Real-time Progress
```
Enhanced scraping: 85%|████████▌ | 837/985 [15:23<02:42, 1.09s/it]
Completed: 837, Failed: 0, Items: 16740, Retries: 23
```

### Log Files

**Activity Log** (`logs/scraper_activity.log`):
```
2024-09-29 12:50:33 - [ThreadPoolExecutor-0_9] - INFO - [Page 10] Page 10 validated with 19 items
2024-09-29 12:50:33 - [ThreadPoolExecutor-0_9] - INFO - [Page 10] Page 10 completed successfully
```

**Error Log** (`logs/scraper_errors.log`):
```
2024-09-29 12:50:35 - [ThreadPoolExecutor-0_12] - ERROR - Error recorded - Type: low_items, Page: 45
2024-09-29 12:50:35 - [ThreadPoolExecutor-0_12] - INFO - Solution attempted: Page retry with validation
```

### Monitor Logs
```bash
# Watch peraturan.go.id logs
tail -f logs/peraturan_go_id_activity.log
tail -f logs/peraturan_go_id_errors.log

# Watch BPK logs
tail -f logs/bpk_activity.log
tail -f logs/bpk_errors.log

# Windows PowerShell
Get-Content logs\bpk_activity.log -Wait -Tail 20

# Check specific errors
grep -i "error" logs/bpk_errors.log
```

## 🔄 Enhanced Retry Logic

### Page Validation
- **Standard Pages**: Must have ≥18 items (configurable)
- **Last Page**: Can have fewer items (validated separately)
- **Automatic Retry**: Pages with insufficient items are automatically retried
- **Max Retries**: Configurable retry limit (default: 5)

### Error Types Tracked
1. **low_items**: Page has fewer items than expected
2. **parse_error**: HTML parsing issues
3. **timeout**: Request timeouts
4. **rate_limit**: Server rate limiting
5. **connection**: Network connection issues

### Solution Attempts
The scraper suggests and attempts solutions:
- **Timeout**: Reduce workers, increase timeout, add delays
- **Rate Limit**: Increase delays, reduce requests, add backoff
- **Parse Error**: Try alternative parsers, skip malformed data
- **Low Items**: Retry page, validate selectors
- **Connection**: Retry request, check network

## 📈 Performance Modes

### Fast Mode (`--fast`)
```bash
python main.py --fast
```
- **30 workers**: Maximum concurrency
- **No PDFs**: Skip downloads for speed
- **Lower validation**: 15 items minimum
- **3 retries**: Faster failure handling
- **Best for**: Quick data collection

### Stable Mode (`--stable`)
```bash
python main.py --stable
```
- **10 workers**: Conservative concurrency
- **PDFs enabled**: Full data collection
- **Standard validation**: 18 items minimum
- **5 retries**: Robust error handling
- **Best for**: Reliable complete scraping

### Custom Mode
```bash
python main.py --workers 20 --no-pdf --retries 2 --min-items 16
```
- **Custom settings**: User-defined parameters
- **Flexible**: Adjust based on needs
- **Best for**: Specific requirements

## 📊 Database Schema

```sql
-- Main perda table
CREATE TABLE perda (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    number TEXT,
    year INTEGER,
    region_name TEXT,
    region_type TEXT,
    detail_url TEXT UNIQUE,
    pdf_url TEXT,
    pdf_path TEXT,
    description TEXT,
    scraped_at TIMESTAMP
);

-- Scraping log table
CREATE TABLE scraping_log (
    id INTEGER PRIMARY KEY,
    page_number INTEGER,
    items_count INTEGER,
    status TEXT,
    error_message TEXT,
    scraped_at TIMESTAMP
);
```

## 🛡 Error Recovery

### State Management
```bash
# Scraping automatically saves state
python main.py

# Resume after interruption (automatic)
python main.py
```

### Manual Recovery
```python
import json

# Check scraping state
with open('scraping_state_enhanced.json') as f:
    state = json.load(f)
    print(f"Scraped: {len(state['scraped_pages'])} pages")
    print(f"Failed: {len(state['failed_pages'])} pages")
```

## 🔧 Troubleshooting

### High Failure Rate
```bash
# Use stable mode
python main.py --stable

# Or reduce workers manually
python main.py --workers 8
```

### Memory Issues
```bash
# Disable PDFs
python main.py --no-pdf

# Reduce workers
python main.py --workers 5
```

### Network Issues
```bash
# Check connection patterns
grep -i "connection\|timeout" logs/scraper_errors.log

# Use conservative settings
python main.py --stable
```

### PDF Download Issues
```bash
# Skip PDFs temporarily
python main_unified.py --source bpk --no-pdf

# Check available disk space
df -h  # Linux/macOS
Get-PSDrive  # Windows PowerShell

# Check PDF download logs
grep -i "pdf" logs/bpk_activity.log
grep -i "pdf" logs/bpk_errors.log
```

### BPK-Specific Issues

**PDF Downloads:**
- BPK PDFs are downloaded from `/Download/{id}/{filename}` endpoint
- Some regulations may not have PDFs available
- PDFs are saved to `docs/bpk/{year}/{region}/`
- Check content-type validation in logs if downloads fail

**Rate Limiting:**
- BPK is a government site - use conservative settings
- Recommended: `--stable` mode with 5 workers
- Increase delays if you see connection errors
- Monitor logs for rate limit indicators

## 📚 Usage Examples

### Scrape All Sources
```bash
# Scrape both databases with default settings
python main_unified.py --all

# Scrape both in fast mode
python main_unified.py --all --fast
```

### Scrape Specific Sources

#### peraturan.go.id Examples
```bash
# Fast collection with PDFs
python main_unified.py --source peraturan --fast

# Ultra mode (maximum speed)
python main_unified.py --source peraturan --ultra

# Custom configuration
python main_unified.py --source peraturan --workers 25 --retries 3
```

#### BPK Examples
```bash
# Stable collection (recommended for BPK)
python main_unified.py --source bpk --stable

# Fast mode without PDFs
python main_unified.py --source bpk --fast --no-pdf

# Custom lightweight scraping
python main_unified.py --source bpk --workers 5 --min-items 8
```

### Development/Testing
```bash
# Test peraturan.go.id with minimal settings
python main_unified.py --source peraturan --workers 3 --min-items 10

# Test BPK with minimal settings
python main_unified.py --source bpk --workers 2 --min-items 5
```

## 🎯 Success Metrics

Recent production scraping session:
- **Pages**: 985/985 (100% success)
- **Items**: 19,660 collected
- **Records**: 17,301 stored (after deduplication)
- **Regions**: 344 unique regions
- **Time Span**: 55 years of regulatory data
- **Runtime**: ~30 minutes with 25 workers
- **Retries**: 0 failed pages (perfect execution)

## 🔄 Development

### Project Setup

#### Using UV
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run with UV
uv run python main.py --workers 5
```

#### Using Python venv
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the scraper
python main.py --workers 5
```

### Development Tips

```bash
# Test with minimal configuration
python main.py --workers 3 --min-items 10

# Monitor logs in real-time (separate terminal)
# Windows PowerShell
Get-Content logs\scraper_activity.log -Wait -Tail 20
# macOS/Linux
tail -f logs/scraper_activity.log

# Check for errors
# Windows PowerShell
Select-String -Path logs\scraper_errors.log -Pattern "ERROR"
# macOS/Linux
grep -i "error" logs/scraper_errors.log
```

### File Overview
- `main_unified.py`: Multi-source CLI entry point (NEW)
- `main.py`: Legacy single-source CLI
- `src/core/base_scraper.py`: Abstract base class for all scrapers
- `src/scrapers/peraturan_go_id_scraper.py`: peraturan.go.id scraper
- `src/scrapers/bpk_scraper.py`: BPK scraper (NEW)
- `src/config/*.py`: Source-specific configurations
- `src/database.py`: Unified database operations
- `logs/`: Source-specific activity and error logs
- `requirements.txt`: Python package dependencies

### Adding New Sources

To add a new data source:
1. Create config file in `src/config/new_source_config.py`
2. Create scraper in `src/scrapers/new_source_scraper.py` extending `BaseScraper`
3. Implement `get_total_pages()`, `parse_page()`, and `scrape_all_with_validation()`
4. Add to `main_unified.py` in the scraper selection logic
5. Test independently before integrating

## 📄 License

This project is for educational and research purposes. Please respect the source website's terms of service and rate limits.

## 👨‍💻 Author

**Nuroji Lukman Syah**
- Email: [dev@csis.or.id](mailto:dev@csis.or.id)
- This script is open for modification and adaptation to suit your needs
- Contributions and improvements are welcome!

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Set up development environment:
   ```bash
   # With UV
   uv pip install -r requirements.txt

   # Or with pip
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
4. Test changes with: `python main.py --workers 3 --min-items 10`
5. Check logs:
   ```bash
   # Windows
   Get-Content logs\scraper_activity.log -Wait -Tail 20
   # macOS/Linux
   tail -f logs/scraper_activity.log
   ```
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open Pull Request

## 📦 Dependencies

All dependencies are listed in `requirements.txt`:
- **requests**: HTTP library for web scraping
- **beautifulsoup4**: HTML parsing
- **lxml**: Fast XML/HTML parser
- **fake-useragent**: Random user agent generation
- **tqdm**: Progress bars
- **tenacity**: Retry logic
- **backoff**: Exponential backoff
- **cachetools**: Caching utilities
- **python-dateutil**: Date parsing utilities

Install with:
```bash
# Using UV (fast)
uv pip install -r requirements.txt

# Using pip (standard)
pip install -r requirements.txt
```
---

**Developer:** Nuroji Lukman Syah | [dev@csis.or.id](mailto:dev@csis.or.id) | Open for modifications and contributions