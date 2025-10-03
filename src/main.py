#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Perda Scraper - Main Module
Features robust scraping with retry logic and detailed logging
"""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for console output
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

from scraper_enhanced import EnhancedPerdaScraper

def run_enhanced_scraper(max_workers=25, download_pdfs=True, max_retries=5, min_items_per_page=18):
    """Run the enhanced scraper with specified configuration"""

    scraper = EnhancedPerdaScraper(
        max_workers=max_workers,
        download_pdfs=download_pdfs,
        max_retries=max_retries,
        min_items_per_page=min_items_per_page
    )

    try:
        print("="*60)
        print("ENHANCED PERDA SCRAPER")
        print("="*60)
        print(f"Configuration:")
        print(f"  Workers: {max_workers}")
        print(f"  Download PDFs: {download_pdfs}")
        print(f"  Max retries: {max_retries}")
        print(f"  Min items per page: {min_items_per_page}")
        print("="*60)

        scraper.scrape_all_with_validation()

    except KeyboardInterrupt:
        print("\n[!] Scraping interrupted by user")
        scraper.save_scraping_state()
        print("[✓] State saved for recovery")

    except Exception as e:
        print(f"\n[✗] Unexpected error: {e}")
        scraper.save_scraping_state()
        raise

    finally:
        scraper.cleanup()

def main():
    """Main entry point - runs with high performance configuration"""
    run_enhanced_scraper(
        max_workers=25,         # High performance
        download_pdfs=True,     # Enable PDF downloads
        max_retries=5,          # Robust retry logic
        min_items_per_page=18   # Validation threshold
    )

if __name__ == "__main__":
    main()