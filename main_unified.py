#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Source Perda Scraper - Unified Entry Point
Supports scraping from multiple Indonesian regulation databases
"""

import sys
import os
import argparse
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scrapers.peraturan_go_id_scraper import create_scraper as create_peraturan_scraper
from scrapers.bpk_scraper import create_scraper as create_bpk_scraper


def main():
    """Unified entry point for multi-source scraping"""
    parser = argparse.ArgumentParser(
        description='Multi-Source Indonesian Regulation Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape both sources
  python main_unified.py --all

  # Scrape only peraturan.go.id (existing source)
  python main_unified.py --source peraturan --workers 30 --fast

  # Scrape only BPK (new source)
  python main_unified.py --source bpk --workers 10 --stable

  # Custom settings for BPK
  python main_unified.py --source bpk --workers 5 --no-pdf
        """
    )

    # Source selection
    parser.add_argument(
        '--source',
        choices=['peraturan', 'bpk', 'all'],
        default='all',
        help='Source to scrape: peraturan (peraturan.go.id), bpk (peraturan.bpk.go.id), or all (default: all)'
    )

    # Worker configuration
    parser.add_argument('--workers', type=int, help='Number of worker threads')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF downloads')
    parser.add_argument('--retries', type=int, help='Max retries per page')
    parser.add_argument('--min-items', type=int, help='Minimum items per page')

    # Preset modes
    parser.add_argument('--fast', action='store_true', help='Fast mode: higher workers, lower validation')
    parser.add_argument('--stable', action='store_true', help='Stable mode: conservative settings')
    parser.add_argument('--ultra', action='store_true', help='Ultra mode: maximum speed (only for peraturan.go.id)')

    args = parser.parse_args()

    # Determine scrapers to run
    scrapers_to_run = []

    if args.source in ['peraturan', 'all']:
        scrapers_to_run.append(('peraturan.go.id', create_peraturan_scraper, {
            'default_workers': 30,
            'fast_workers': 40,
            'stable_workers': 15,
            'ultra_workers': 50,
        }))

    if args.source in ['bpk', 'all']:
        scrapers_to_run.append(('BPK', create_bpk_scraper, {
            'default_workers': 10,
            'fast_workers': 15,
            'stable_workers': 5,
            'ultra_workers': None,  # Ultra mode not recommended for BPK
        }))

    # Run each scraper
    for source_name, scraper_factory, config in scrapers_to_run:
        print(f"\n{'='*70}")
        print(f"STARTING SCRAPER: {source_name}")
        print(f"{'='*70}\n")

        # Determine configuration based on mode
        if args.ultra and config['ultra_workers']:
            workers = config['ultra_workers']
            download_pdfs = True
            retries = 2
            min_items = 10
            print(f"⚡ ULTRA MODE: {workers} workers")
        elif args.fast:
            workers = config['fast_workers']
            download_pdfs = True
            retries = 3
            min_items = 12 if source_name == 'peraturan.go.id' else 8
            print(f"🚀 FAST MODE: {workers} workers")
        elif args.stable:
            workers = config['stable_workers']
            download_pdfs = not args.no_pdf
            retries = 5
            min_items = 18 if source_name == 'peraturan.go.id' else 8
            print(f"🛡️ STABLE MODE: {workers} workers")
        else:
            workers = args.workers if args.workers else config['default_workers']
            download_pdfs = not args.no_pdf
            retries = args.retries if args.retries else 5
            min_items = args.min_items if args.min_items else (18 if source_name == 'peraturan.go.id' else 8)
            print(f"⚙️ CUSTOM MODE: {workers} workers")

        # Create and run scraper
        try:
            scraper = scraper_factory(
                max_workers=workers,
                download_pdfs=download_pdfs,
                max_retries=retries,
                min_items_per_page=min_items
            )

            scraper.scrape_all_with_validation()

            print(f"\n✅ {source_name} scraping completed successfully\n")

        except KeyboardInterrupt:
            print(f"\n⚠️ {source_name} scraping interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ {source_name} scraping failed: {e}\n")
            continue
        finally:
            if 'scraper' in locals():
                scraper.cleanup()

    print(f"\n{'='*70}")
    print("ALL SCRAPING TASKS COMPLETED")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()