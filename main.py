#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Perda Scraper - Streamlined Entry Point
Simple interface to the enhanced scraping functionality
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import run_enhanced_scraper

def main():
    """Streamlined entry point with command line options"""
    parser = argparse.ArgumentParser(description='Enhanced Perda Scraper - Optimized')
    parser.add_argument('--workers', type=int, default=30, help='Number of worker threads (default: 30)')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF downloads for faster scraping')
    parser.add_argument('--retries', type=int, default=3, help='Max retries per page (default: 3)')
    parser.add_argument('--min-items', type=int, default=15, help='Minimum items per page (default: 15)')
    parser.add_argument('--fast', action='store_true', help='Fast mode: 40 workers with PDFs, lower validation')
    parser.add_argument('--stable', action='store_true', help='Stable mode: 15 workers, conservative settings')
    parser.add_argument('--ultra', action='store_true', help='Ultra mode: 50 workers, maximum speed')
    parser.add_argument('--with-pdf', action='store_true', help='Force PDF downloads (default: enabled unless --no-pdf)')

    args = parser.parse_args()

    # Preset configurations - Optimized for speed
    if args.ultra:
        workers = 50
        download_pdfs = True
        retries = 2
        min_items = 10
        print("⚡ ULTRA MODE: Maximum speed (50 workers) with PDFs")
    elif args.fast:
        workers = 40
        download_pdfs = True
        retries = 3
        min_items = 12
        print("🚀 FAST MODE: High speed (40 workers) with PDFs")
    elif args.with_pdf:
        workers = 30
        download_pdfs = True
        retries = 3
        min_items = 15
        print("📥 PDF MODE: Optimized (30 workers) with PDF downloads")
    elif args.stable:
        workers = 15
        download_pdfs = not args.no_pdf
        retries = 4
        min_items = 15
        print("🛡️ STABLE MODE: Conservative settings (15 workers)")
    else:
        workers = args.workers
        download_pdfs = not args.no_pdf
        retries = args.retries
        min_items = args.min_items
        if download_pdfs:
            print(f"⚙️ CUSTOM MODE: {workers} workers with PDFs")
        else:
            print(f"⚙️ CUSTOM MODE: {workers} workers without PDFs")

    # Run the enhanced scraper
    run_enhanced_scraper(
        max_workers=workers,
        download_pdfs=download_pdfs,
        max_retries=retries,
        min_items_per_page=min_items
    )

if __name__ == "__main__":
    main()
