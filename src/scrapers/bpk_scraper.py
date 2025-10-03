#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BPK Peraturan Scraper (peraturan.bpk.go.id)
Scraper for Indonesian regulations from BPK database
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import re
import sys

# Import shared components
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_scraper import BaseScraper
from database import PerdaDatabase
from config.bpk_config import *


class BPKScraper(BaseScraper):
    """Scraper for peraturan.bpk.go.id"""

    def __init__(self, max_workers=DEFAULT_WORKERS, download_pdfs=DEFAULT_DOWNLOAD_PDFS,
                 max_retries=DEFAULT_MAX_RETRIES, min_items_per_page=MIN_ITEMS_PER_PAGE):
        """Initialize BPK scraper"""
        super().__init__(
            source_name=SOURCE_NAME,
            base_url=BASE_URL,
            max_workers=max_workers,
            download_pdfs=download_pdfs,
            max_retries=max_retries,
            min_items_per_page=min_items_per_page
        )

        self.search_url = SEARCH_URL
        self.db = PerdaDatabase()  # Main database for reading state
        self.worker_dbs = {}  # Track per-worker databases

        # PDF download directory
        if download_pdfs:
            self.pdf_base_dir = Path(PDF_BASE_DIR)
            self.pdf_base_dir.mkdir(parents=True, exist_ok=True)

    def get_worker_db(self, worker_id):
        """Get or create a worker-specific database"""
        if worker_id not in self.worker_dbs:
            self.worker_dbs[worker_id] = PerdaDatabase(worker_id=worker_id)
        return self.worker_dbs[worker_id]

    def get_total_pages(self) -> int:
        """Get total number of pages from the website"""
        try:
            session = self.get_session()
            params = self._build_search_params(1)

            response = session.get(self.search_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find pagination info
            # BPK pagination only shows first 10 pages, not total
            # We'll use the configured expected total instead

            # Try to find pagination to verify site is working
            pagination = soup.find_all('a', class_='page-link')
            if pagination:
                self.activity_logger.info(f"Pagination found, using configured total: {EXPECTED_TOTAL_PAGES} pages")
            else:
                self.activity_logger.warning(f"No pagination found, using configured total: {EXPECTED_TOTAL_PAGES} pages")

            return EXPECTED_TOTAL_PAGES

        except Exception as e:
            self.error_logger.error(f"Error getting total pages: {e}")
            return EXPECTED_TOTAL_PAGES

    def _build_search_params(self, page_num: int) -> list:
        """Build search parameters with multiple jenis values"""
        # Build list of tuples for multiple jenis parameters
        params = [
            ('keywords', SEARCH_PARAMS['keywords']),
            ('tentang', SEARCH_PARAMS['tentang']),
            ('nomor', SEARCH_PARAMS['nomor']),
        ]

        # Add multiple jenis parameters
        jenis_list = SEARCH_PARAMS['jenis']
        if isinstance(jenis_list, list):
            for jenis in jenis_list:
                params.append(('jenis', jenis))
        else:
            params.append(('jenis', jenis_list))

        params.append(('p', page_num))
        return params

    def parse_page(self, page_num: int) -> list:
        """Parse a single page and return list of regulations"""
        try:
            session = self.get_session()
            params = self._build_search_params(page_num)

            # Add delay
            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

            response = session.get(self.search_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all regulation cards
            cards = soup.find_all('div', class_='card')
            items = []

            for card in cards:
                try:
                    item = self._parse_card(card)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.error_logger.error(f"Error parsing card on page {page_num}: {e}")
                    continue

            self.activity_logger.info(f"Page {page_num}: Found {len(items)} items")
            return items

        except requests.exceptions.RequestException as e:
            self.error_logger.error(f"Request error on page {page_num}: {e}")
            raise
        except Exception as e:
            self.error_logger.error(f"Error parsing page {page_num}: {e}")
            raise

    def download_pdf(self, pdf_url: str, year: int, region_name: str, title: str) -> str:
        """Download PDF file to organized directory structure"""
        if not pdf_url or not self.download_pdfs:
            return None

        try:
            # Create directory structure: docs/bpk/year/region/
            year_str = str(year) if year else "unknown_year"
            region_str = re.sub(r'[^\w\s-]', '', region_name or "unknown_region").strip()
            region_str = re.sub(r'[-\s]+', '_', region_str)

            pdf_dir = self.pdf_base_dir / year_str / region_str
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from title
            filename = re.sub(r'[^\w\s-]', '', title[:100]).strip()
            filename = re.sub(r'[-\s]+', '_', filename)
            filename = f"{filename}.pdf"

            pdf_path = pdf_dir / filename

            # Skip if already downloaded
            if pdf_path.exists():
                self.activity_logger.info(f"PDF already exists: {pdf_path}")
                return str(pdf_path)

            # Download PDF with retry logic
            session = self.get_session()
            for attempt in range(3):
                try:
                    # Add delay before download
                    time.sleep(random.uniform(1, 2))

                    response = session.get(pdf_url, stream=True, timeout=45)
                    response.raise_for_status()

                    # Check if response is actually a PDF or binary file
                    content_type = response.headers.get('content-type', '').lower()
                    # BPK returns 'application/octet-stream' for PDFs - accept it
                    # Only reject if it's clearly not a binary file (e.g., HTML error page)
                    if 'html' in content_type or 'text' in content_type:
                        self.error_logger.warning(f"URL returned non-binary content: {pdf_url} (got {content_type})")
                        return None

                    # Save PDF
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.activity_logger.info(f"Downloaded PDF: {pdf_path}")
                    return str(pdf_path)

                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        self.error_logger.error(f"Failed to download PDF from {pdf_url}: {e}")
                        break

        except Exception as e:
            self.error_logger.error(f"Error downloading PDF: {e}")

        return None

    def _parse_card(self, card) -> dict:
        """Parse individual regulation card"""
        try:
            # Find title and detail link
            title_link = card.find('a', href=re.compile(r'/Details/'))
            if not title_link:
                return None

            title = title_link.get_text(strip=True)
            detail_url = urljoin(self.base_url, title_link['href'])

            # Extract regulation info (number and year)
            reg_info = card.find('div', class_='fw-semibold')
            number = None
            year = None
            region_name = None

            if reg_info:
                info_text = reg_info.get_text(strip=True)
                # Pattern: "Peraturan Daerah (Perda) Kabupaten Bandung Nomor 55 Tahun 2025"

                # Extract region
                region_match = re.search(r'(Kabupaten|Kota|Provinsi)\s+([^N]+)', info_text)
                if region_match:
                    region_name = f"{region_match.group(1)} {region_match.group(2).strip()}"

                # Extract number
                number_match = re.search(r'Nomor\s+(\d+)', info_text)
                if number_match:
                    number = number_match.group(1)

                # Extract year
                year_match = re.search(r'Tahun\s+(\d{4})', info_text)
                if year_match:
                    year = int(year_match.group(1))

            # Extract description/abstract
            description = None
            desc_div = card.find('div', class_='text-gray-700')
            if desc_div:
                description = desc_div.get_text(strip=True)

            # Extract PDF download link if available
            pdf_url = None
            pdf_link = card.find('a', href=re.compile(r'/Download/'))
            if pdf_link:
                pdf_url = urljoin(self.base_url, pdf_link['href'])

            # Extract status/metadata
            status = None
            badges = card.find_all('span', class_='badge')
            if badges:
                status = ', '.join([b.get_text(strip=True) for b in badges])

            # Determine region type
            region_type = None
            if region_name:
                if 'Kabupaten' in region_name:
                    region_type = 'Kabupaten'
                elif 'Kota' in region_name:
                    region_type = 'Kota'
                elif 'Provinsi' in region_name:
                    region_type = 'Provinsi'

            return {
                'source': SOURCE_NAME,
                'title': title,
                'number': number,
                'year': year,
                'region_name': region_name,
                'region_type': region_type,
                'detail_url': detail_url,
                'pdf_url': pdf_url,
                'description': description,
                'status': status,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.error_logger.error(f"Error parsing card: {e}")
            return None

    def scrape_all_with_validation(self):
        """Main scraping method"""
        try:
            # Get total pages
            total_pages = self.get_total_pages()

            print(f"\n{'='*60}")
            print(f"BPK PERATURAN SCRAPER")
            print(f"{'='*60}")
            print(f"Source: {self.base_url}")
            print(f"Total pages: {total_pages}")
            print(f"Items per page: ~{ITEMS_PER_PAGE}")
            print(f"Workers: {self.max_workers}")
            print(f"Download PDFs: {self.download_pdfs}")
            print(f"{'='*60}\n")

            # Load previous state if exists
            self.load_scraping_state()

            # Determine pages to scrape
            pages_to_scrape = [p for p in range(1, total_pages + 1) if p not in self.scraped_pages]

            self.activity_logger.info(f"Starting scraping: {len(pages_to_scrape)} pages to scrape")

            # Scrape with thread pool
            # Assign worker IDs to pages for database partitioning
            page_to_worker = {page: idx % self.max_workers for idx, page in enumerate(pages_to_scrape)}

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._scrape_page_with_retry, page, page_to_worker[page]): page
                          for page in pages_to_scrape}

                with tqdm(total=len(pages_to_scrape), desc="BPK scraping") as pbar:
                    for future in as_completed(futures):
                        page_num = futures[future]
                        try:
                            worker_id, items = future.result()
                            if items:
                                # Get worker-specific database
                                worker_db = self.get_worker_db(worker_id)

                                # Download PDFs and save to database
                                for item in items:
                                    # Download PDF if URL exists
                                    if item.get('pdf_url') and self.download_pdfs:
                                        # Update tqdm description with current file
                                        title_short = item.get('title', 'untitled')[:50]
                                        pbar.set_description(f"BPK scraping [{title_short}...]")

                                        pdf_path = self.download_pdf(
                                            pdf_url=item['pdf_url'],
                                            year=item.get('year'),
                                            region_name=item.get('region_name'),
                                            title=item.get('title', 'untitled')
                                        )
                                        if pdf_path:
                                            item['pdf_path'] = pdf_path

                                    # Save to worker-specific database (no locks!)
                                    worker_db.insert_perda(item)

                                with self.progress_lock:
                                    self.scraped_pages.add(page_num)
                                    self.total_items_scraped += len(items)

                                worker_db.log_scraping(page_num, len(items), 'success')

                            # Reset description and update progress
                            pbar.set_description("BPK scraping")
                            pbar.update(1)
                            pbar.set_postfix({
                                'page': page_num,
                                'completed': len(self.scraped_pages),
                                'failed': len(self.failed_pages),
                                'items': self.total_items_scraped
                            })

                        except Exception as e:
                            self.error_logger.error(f"Failed page {page_num}: {e}")
                            with self.data_lock:
                                self.failed_pages[page_num] = str(e)
                            # Log to main database for failures (shouldn't cause much contention)
                            self.db.log_scraping(page_num, 0, 'failed', str(e))

            # Merge worker databases into main database
            print(f"\n{'='*60}")
            print(f"MERGING WORKER DATABASES")
            print(f"{'='*60}\n")

            merged_count = PerdaDatabase.merge_worker_databases()

            print(f"Merged {merged_count} records from {len(self.worker_dbs)} worker databases\n")

            # Final statistics
            print(f"{'='*60}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*60}")
            print(f"Completed pages: {len(self.scraped_pages)}")
            print(f"Failed pages: {len(self.failed_pages)}")
            print(f"Total items: {self.total_items_scraped}")
            print(f"{'='*60}\n")

            # Save final state
            self.save_scraping_state()

        except KeyboardInterrupt:
            print("\n[!] Scraping interrupted by user")
            self.save_scraping_state()
            raise
        except Exception as e:
            self.error_logger.error(f"Fatal error in scraping: {e}")
            self.save_scraping_state()
            raise

    def _scrape_page_with_retry(self, page_num: int, worker_id: int) -> tuple:
        """Scrape a single page with retry logic"""
        for attempt in range(self.max_retries):
            try:
                items = self.parse_page(page_num)

                # Validate item count
                if len(items) < self.min_items_per_page and page_num < self.get_total_pages():
                    self.activity_logger.warning(
                        f"Page {page_num}: Low item count ({len(items)}), attempt {attempt + 1}/{self.max_retries}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(random.uniform(2, 5))
                        continue

                return (worker_id, items)

            except Exception as e:
                self.error_logger.error(f"Page {page_num} attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(random.uniform(3, 6))
                else:
                    raise

        return (worker_id, [])


def create_scraper(**kwargs):
    """Factory function to create BPK scraper instance"""
    return BPKScraper(**kwargs)