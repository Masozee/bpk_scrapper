"""
Configuration for peraturan.go.id scraper
"""

# Source identifier
SOURCE_NAME = "peraturan_go_id"

# Base URLs
BASE_URL = "https://peraturan.go.id"
PERDA_URL = f"{BASE_URL}/perda"

# Scraping parameters
ITEMS_PER_PAGE = 20
MIN_ITEMS_PER_PAGE = 18  # Validation threshold
EXPECTED_TOTAL_ITEMS = 19686

# Default scraper settings
DEFAULT_WORKERS = 25
DEFAULT_MAX_RETRIES = 5
DEFAULT_DOWNLOAD_PDFS = True

# Request settings
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = (0.5, 1.5)  # Random delay range in seconds

# PDF download settings
PDF_BASE_DIR = "docs/peraturan_go_id"
PDF_ORGANIZE_BY_YEAR = True
PDF_ORGANIZE_BY_REGION = True