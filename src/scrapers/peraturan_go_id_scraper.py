#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Peraturan.go.id Scraper
Wrapper for existing enhanced scraper with source tracking
"""

import sys
from pathlib import Path

# Import existing scraper
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper_enhanced import EnhancedPerdaScraper as BaseEnhancedScraper
from config.peraturan_go_id_config import *


class PeraturanGoIdScraper(BaseEnhancedScraper):
    """Scraper for peraturan.go.id with source tracking"""

    def __init__(self, max_workers=DEFAULT_WORKERS, download_pdfs=DEFAULT_DOWNLOAD_PDFS,
                 max_retries=DEFAULT_MAX_RETRIES, min_items_per_page=MIN_ITEMS_PER_PAGE):
        """Initialize with source-specific configuration"""
        super().__init__(
            max_workers=max_workers,
            download_pdfs=download_pdfs,
            max_retries=max_retries,
            min_items_per_page=min_items_per_page
        )

        # Override source name
        self.source_name = SOURCE_NAME

        # Override state file
        self.state_file = Path(f'scraping_state_{SOURCE_NAME}.json')

        # Override PDF base directory
        if download_pdfs:
            self.pdf_base_dir = Path(PDF_BASE_DIR)
            self.pdf_base_dir.mkdir(parents=True, exist_ok=True)

    def save_to_database(self, items):
        """Save items with source field"""
        for item in items:
            item['source'] = self.source_name
        return super().save_to_database(items)


def create_scraper(**kwargs):
    """Factory function to create scraper instance"""
    return PeraturanGoIdScraper(**kwargs)