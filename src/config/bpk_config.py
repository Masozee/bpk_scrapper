"""
Configuration for peraturan.bpk.go.id scraper
"""

# Source identifier
SOURCE_NAME = "bpk"

# Base URLs
BASE_URL = "https://peraturan.bpk.go.id"
SEARCH_URL = f"{BASE_URL}/Search"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/Details/{{id}}/{{slug}}"
PDF_DOWNLOAD_URL_TEMPLATE = f"{BASE_URL}/Download/{{id}}/{{filename}}"

# Search parameters
# Regulation types (jenis):
# 19 = Peraturan Daerah (Perda)
# 20 = Peraturan Gubernur
# 23 = Peraturan Bupati/Walikota
# 30 = Keputusan
# To scrape only specific types, modify JENIS_TYPES below
JENIS_TYPES = ["20", "23", "30"]  # List of regulation types to scrape

SEARCH_PARAMS = {
    "keywords": "",
    "tentang": "",
    "nomor": "",
    "jenis": JENIS_TYPES,  # Multiple regulation types
    "p": 1  # BPK uses 'p' not 'page' for pagination
}

# Scraping parameters
ITEMS_PER_PAGE = 10
MIN_ITEMS_PER_PAGE = 8  # Lower threshold due to fewer items per page
EXPECTED_TOTAL_PAGES = 5893  # Approximate, may change

# Default scraper settings (more conservative for BPK)
DEFAULT_WORKERS = 10  # Lower to avoid rate limiting
DEFAULT_MAX_RETRIES = 5
DEFAULT_DOWNLOAD_PDFS = True

# Request settings (more conservative)
REQUEST_TIMEOUT = 45
DELAY_BETWEEN_REQUESTS = (2.0, 4.0)  # Longer delays for government site

# PDF download settings
PDF_BASE_DIR = "docs/bpk"
PDF_ORGANIZE_BY_YEAR = True
PDF_ORGANIZE_BY_REGION = True

# Selector configuration for card-based layout
SELECTORS = {
    "card_container": "div.card",
    "title": "a",
    "regulation_info": "div.fw-semibold",
    "detail_link": "a[href*='/Details/']",
    "pdf_link": "a[href*='/Download/']",
    "description": "div.text-gray-700",
    "metadata": "span.badge"
}