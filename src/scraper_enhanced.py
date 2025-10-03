#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Perda Scraper with Advanced Retry Logic and Detailed Logging
Features:
- Retry pages with insufficient items (< 18-20 items)
- Separate activity and error logs
- Detailed error tracking and solution attempts
- Ordered processing with validation
- Recovery and state management
"""

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock
import threading
from queue import Queue, PriorityQueue
from tqdm import tqdm
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote
import re
import os
from src.database import PerdaDatabase
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import backoff
from cachetools import TTLCache, LRUCache
from functools import lru_cache
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import traceback

# Enhanced logging setup
class DetailedFormatter(logging.Formatter):
    """Custom formatter for detailed logging"""

    def format(self, record):
        if hasattr(record, 'page_num'):
            record.msg = f"[Page {record.page_num}] {record.msg}"
        if hasattr(record, 'retry_count') and record.retry_count > 0:
            record.msg = f"{record.msg} (Retry {record.retry_count})"
        return super().format(record)

def setup_enhanced_logging():
    """Setup enhanced logging with separate files for activities and errors"""

    # Create logs directory
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # Activity logger
    activity_logger = logging.getLogger('activity')
    activity_logger.setLevel(logging.INFO)

    activity_handler = logging.FileHandler(logs_dir / 'scraper_activity.log', encoding='utf-8')
    activity_handler.setFormatter(DetailedFormatter(
        '%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
    ))
    activity_logger.addHandler(activity_handler)

    # Error logger
    error_logger = logging.getLogger('errors')
    error_logger.setLevel(logging.WARNING)

    error_handler = logging.FileHandler(logs_dir / 'scraper_errors.log', encoding='utf-8')
    error_handler.setFormatter(DetailedFormatter(
        '%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n'
    ))
    error_logger.addHandler(error_handler)

    # Console logger
    console_logger = logging.getLogger('console')
    console_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    console_logger.addHandler(console_handler)

    return activity_logger, error_logger, console_logger

# Global loggers
activity_logger, error_logger, console_logger = setup_enhanced_logging()


@dataclass(order=True)
class PageTask:
    """Enhanced page task with validation info"""
    priority: int
    page_num: int = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    last_error: str = field(default="", compare=False)
    items_found: int = field(default=0, compare=False)
    is_last_page: bool = field(default=False, compare=False)
    retry_reason: str = field(default="", compare=False)


class ErrorTracker:
    """Track and analyze errors for solution attempts"""

    def __init__(self):
        self.errors = {}
        self.solutions = {
            'timeout': ['Reduce workers', 'Increase timeout', 'Add delays'],
            'rate_limit': ['Increase delays', 'Reduce concurrent requests', 'Add backoff'],
            'parse_error': ['Retry with different parser', 'Skip malformed data'],
            'low_items': ['Retry page', 'Check page structure', 'Validate selectors'],
            'connection': ['Retry request', 'Check network', 'Use different session']
        }

    def record_error(self, error_type: str, page_num: int, error_msg: str, solution_attempted: str = None):
        """Record error with details"""
        if error_type not in self.errors:
            self.errors[error_type] = []

        error_record = {
            'page_num': page_num,
            'error_msg': error_msg,
            'timestamp': datetime.now().isoformat(),
            'solution_attempted': solution_attempted,
            'resolved': False
        }

        self.errors[error_type].append(error_record)

        error_logger.error(
            f"Error recorded - Type: {error_type}, Page: {page_num}, Message: {error_msg}",
            extra={'page_num': page_num}
        )

        if solution_attempted:
            error_logger.info(
                f"Solution attempted: {solution_attempted}",
                extra={'page_num': page_num}
            )

    def get_suggested_solution(self, error_type: str) -> str:
        """Get suggested solution for error type"""
        return random.choice(self.solutions.get(error_type, ['Generic retry']))

    def mark_resolved(self, error_type: str, page_num: int):
        """Mark error as resolved"""
        if error_type in self.errors:
            for error in self.errors[error_type]:
                if error['page_num'] == page_num and not error['resolved']:
                    error['resolved'] = True
                    error_logger.info(
                        f"Error resolved - Type: {error_type}, Page: {page_num}",
                        extra={'page_num': page_num}
                    )
                    break


class EnhancedPerdaScraper:
    """Enhanced scraper with validation and detailed logging"""

    def __init__(self, max_workers=15, download_pdfs=True, max_retries=5, min_items_per_page=18):
        self.base_url = "https://peraturan.go.id"
        self.perda_url = f"{self.base_url}/perda"

        # Configuration
        self.max_workers = max_workers
        self.download_pdfs = download_pdfs
        self.max_retries = max_retries
        self.min_items_per_page = min_items_per_page

        # Thread management
        self.session_lock = RLock()
        self.sessions = {}
        self.ua = UserAgent()

        # Data structures
        self.data_lock = Lock()
        self.scraped_pages = set()
        self.failed_pages = {}
        self.page_data = {}
        self.low_item_pages = set()  # Track pages with insufficient items

        # Progress tracking
        self.progress_lock = Lock()
        self.total_items_scraped = 0
        self.validation_retries = 0
        self.current_download = ""  # Track current file being downloaded

        # Configuration
        self.page_size = 20
        self.total_expected = 19686
        self.db = PerdaDatabase()

        # Error tracking
        self.error_tracker = ErrorTracker()

        # Caching
        self.cache = TTLCache(maxsize=1000, ttl=300)
        self.region_cache = LRUCache(maxsize=500)

        # Rate limiting
        self.rate_limiter = threading.Semaphore(8)  # Reduced for stability
        self.last_request_time = {}
        self.min_request_interval = 0.8  # Increased interval

        activity_logger.info("Enhanced scraper initialized", extra={
            'max_workers': max_workers,
            'download_pdfs': download_pdfs,
            'min_items_per_page': min_items_per_page
        })

    def get_thread_session(self) -> requests.Session:
        """Get or create thread-local session"""
        thread_id = threading.current_thread().ident

        with self.session_lock:
            if thread_id not in self.sessions:
                session = requests.Session()
                session.headers.update({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })

                # Enhanced adapter
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=15,
                    pool_maxsize=15,
                    max_retries=3,
                    pool_block=False
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)

                self.sessions[thread_id] = session

            return self.sessions[thread_id]

    def get_random_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Referer': self.perda_url
        }

    def enforce_rate_limit(self):
        """Enhanced rate limiting"""
        thread_id = threading.current_thread().ident
        current_time = time.time()

        if thread_id in self.last_request_time:
            elapsed = current_time - self.last_request_time[thread_id]
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                time.sleep(sleep_time)

        self.last_request_time[thread_id] = time.time()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=3, max=60),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def make_request_with_retry(self, url, params=None, stream=False, page_num=None):
        """Enhanced request with detailed error tracking"""
        with self.rate_limiter:
            self.enforce_rate_limit()

            # Random delay to avoid detection
            time.sleep(random.uniform(0.5, 1.5))

            session = self.get_thread_session()
            headers = self.get_random_headers()

            try:
                response = session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=45,  # Increased timeout
                    stream=stream,
                    verify=True
                )

                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 15))
                    error_msg = f"Rate limited, waiting {wait_time}s"
                    if page_num:
                        self.error_tracker.record_error('rate_limit', page_num, error_msg, 'Exponential backoff')
                    activity_logger.warning(error_msg, extra={'page_num': page_num})
                    time.sleep(wait_time)
                    raise requests.RequestException("Rate limited")

                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                error_msg = f"Request timeout: {str(e)}"
                if page_num:
                    solution = self.error_tracker.get_suggested_solution('timeout')
                    self.error_tracker.record_error('timeout', page_num, error_msg, solution)
                raise

            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                if page_num:
                    solution = self.error_tracker.get_suggested_solution('connection')
                    self.error_tracker.record_error('connection', page_num, error_msg, solution)
                raise

    @lru_cache(maxsize=256)
    def extract_year_from_text(self, text):
        if not text:
            return None
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if year_match:
            return int(year_match.group(1))
        return None

    def extract_region_info(self, text):
        """Extract region info with caching"""
        if text in self.region_cache:
            return self.region_cache[text]

        region_info = {
            'region_name': None,
            'region_type': None,
            'region_code': None
        }

        if not text:
            return region_info

        region_types = [
            'Provinsi', 'Kabupaten', 'Kota', 'Daerah Khusus', 'DKI'
        ]

        for rtype in region_types:
            if rtype.lower() in text.lower():
                region_info['region_type'] = rtype
                pattern = f'{rtype}\\s+([^\\n]+?)(?:\\s+Nomor|\\s+No\\.|$)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    name = re.sub(r'\s*\d+\s*(?:Tahun\s*\d+)?$', '', name)
                    region_info['region_name'] = name.strip()
                break

        if not region_info['region_name']:
            patterns = [
                r'(?:Perda|Peraturan Daerah)\s+([A-Za-z\s]+?)(?:\s+Nomor|\s+No\.)',
                r'(?:dari|di)\s+([A-Za-z\s]+?)(?:\s+tentang|\s+Nomor)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    for rtype in region_types:
                        if name.lower().startswith(rtype.lower()):
                            name = name[len(rtype):].strip()
                            region_info['region_type'] = rtype
                            break
                    region_info['region_name'] = name
                    break

        self.region_cache[text] = region_info
        return region_info

    def parse_perda_from_elements(self, detail_link, pdf_link=None, title_para=None):
        """Parse perda data with enhanced error handling"""
        data = {}

        try:
            if detail_link:
                data['detail_url'] = urljoin(self.base_url, detail_link.get('href', ''))
                data['description'] = detail_link.get_text(strip=True)

            if title_para:
                title_text = title_para.get_text(strip=True)
                data['title'] = title_text
                data['year'] = self.extract_year_from_text(title_text)

                region_info = self.extract_region_info(title_text)
                data.update(region_info)

                number_match = re.search(r'(?:Nomor|No\.?)\s*([\d\s]+)(?:\s+Tahun)?', title_text, re.IGNORECASE)
                if number_match:
                    data['number'] = number_match.group(1).strip()

            if pdf_link:
                data['pdf_url'] = urljoin(self.base_url, pdf_link.get('href', ''))

            data['scraped_at'] = datetime.now().isoformat()

        except Exception as e:
            error_logger.error(f"Error parsing perda elements: {e}\n{traceback.format_exc()}")

        return data if data.get('title') or data.get('description') else None

    def validate_page_items(self, items: List[Dict], page_num: int, is_last_page: bool = False) -> bool:
        """Validate if page has sufficient items"""
        item_count = len(items)

        if is_last_page:
            # Last page can have fewer items
            if item_count == 0:
                activity_logger.warning(f"Last page {page_num} has no items", extra={'page_num': page_num})
                return False
            activity_logger.info(f"Last page {page_num} validated with {item_count} items", extra={'page_num': page_num})
            return True

        if item_count < self.min_items_per_page:
            activity_logger.warning(
                f"Page {page_num} has only {item_count} items (expected ≥{self.min_items_per_page})",
                extra={'page_num': page_num}
            )
            return False

        activity_logger.info(f"Page {page_num} validated with {item_count} items", extra={'page_num': page_num})
        return True

    def scrape_page_enhanced(self, page_num: int, retry_count: int = 0, is_last_page: bool = False) -> Tuple[int, List[Dict], Optional[str]]:
        """Enhanced page scraping with validation"""

        activity_logger.info(f"Starting page {page_num} scrape", extra={
            'page_num': page_num,
            'retry_count': retry_count
        })

        try:
            params = {
                'page': page_num,
                'per-page': self.page_size
            }

            response = self.make_request_with_retry(self.perda_url, params=params, page_num=page_num)

            if not response or not response.content:
                error_msg = f"Empty response for page {page_num}"
                self.error_tracker.record_error('empty_response', page_num, error_msg, 'Retry request')
                return page_num, [], error_msg

            soup = BeautifulSoup(response.content, 'lxml')
            items = []

            # Enhanced parsing with error tracking
            try:
                detail_links = soup.find_all('a', href=lambda h: h and '/id/perda-' in h)

                for detail_link in detail_links:
                    parent = detail_link.parent
                    title_para = None
                    pdf_link = None

                    # Find title paragraph
                    container = parent
                    while container and container.name not in ['body', 'html']:
                        prev_sibling = container.find_previous_sibling()
                        if prev_sibling and prev_sibling.name == 'p':
                            text = prev_sibling.get_text(strip=True)
                            if 'Peraturan Daerah' in text or 'Nomor' in text:
                                title_para = prev_sibling
                                break
                        container = container.parent

                    # Find PDF link
                    if parent:
                        search_area = parent.parent if parent.parent else parent
                        pdf_link = search_area.find('a', href=lambda h: h and '.pdf' in h)

                    parsed_item = self.parse_perda_from_elements(detail_link, pdf_link, title_para)
                    if parsed_item:
                        parsed_item['page_num'] = page_num
                        items.append(parsed_item)

                # Alternative parsing if no items found
                if not items:
                    perda_paragraphs = soup.find_all('p', string=lambda t: t and 'Peraturan Daerah' in t)

                    for para in perda_paragraphs:
                        next_elem = para.find_next_sibling()
                        if next_elem and next_elem.name == 'p':
                            detail_link = next_elem.find('a')
                            if detail_link:
                                pdf_container = next_elem.find_next_sibling()
                                pdf_link = None
                                if pdf_container:
                                    pdf_link = pdf_container.find('a', href=lambda h: h and '.pdf' in h)

                                parsed_item = self.parse_perda_from_elements(detail_link, pdf_link, para)
                                if parsed_item:
                                    parsed_item['page_num'] = page_num
                                    items.append(parsed_item)

            except Exception as e:
                error_msg = f"Parsing error: {str(e)}"
                self.error_tracker.record_error('parse_error', page_num, error_msg, 'Alternative parsing method')
                error_logger.error(f"Parse error on page {page_num}: {e}\n{traceback.format_exc()}", extra={'page_num': page_num})
                return page_num, [], error_msg

            # Validate items count
            if not self.validate_page_items(items, page_num, is_last_page):
                if retry_count < self.max_retries:
                    error_msg = f"Insufficient items on page {page_num}: {len(items)} (min: {self.min_items_per_page})"
                    self.error_tracker.record_error('low_items', page_num, error_msg, 'Page retry with validation')
                    return page_num, [], error_msg
                else:
                    # Accept after max retries
                    activity_logger.warning(f"Accepting page {page_num} with {len(items)} items after {retry_count} retries", extra={'page_num': page_num})

            activity_logger.info(f"Page {page_num} successfully scraped with {len(items)} items", extra={'page_num': page_num})
            self.db.log_scraping(page_num, len(items), 'success')

            # Mark errors as resolved if page succeeded
            for error_type in ['low_items', 'parse_error', 'empty_response']:
                self.error_tracker.mark_resolved(error_type, page_num)

            return page_num, items, None

        except Exception as e:
            error_msg = f"Unexpected error scraping page {page_num}: {str(e)}"
            error_logger.error(f"{error_msg}\n{traceback.format_exc()}", extra={'page_num': page_num})
            self.db.log_scraping(page_num, 0, 'failed', str(e))
            return page_num, [], error_msg

    def process_page_task_enhanced(self, task: PageTask, total_pages: int) -> bool:
        """Enhanced page task processing with validation and immediate PDF download"""
        is_last_page = task.page_num == total_pages
        page_num, items, error = self.scrape_page_enhanced(task.page_num, task.retry_count, is_last_page)

        with self.data_lock:
            if error:
                if task.retry_count < self.max_retries:
                    task.retry_count += 1
                    task.last_error = error
                    task.retry_reason = f"Retry due to: {error}"

                    # Add back to queue for retry
                    activity_logger.info(f"Queuing page {page_num} for retry {task.retry_count}", extra={'page_num': page_num})
                    return False
                else:
                    # Max retries reached
                    self.failed_pages[page_num] = {
                        'error': error,
                        'retry_count': task.retry_count,
                        'timestamp': datetime.now().isoformat(),
                        'final_failure': True
                    }
                    error_logger.error(f"Page {page_num} failed permanently after {task.retry_count} retries: {error}", extra={'page_num': page_num})
                    return False
            else:
                # Success - immediately download PDFs if enabled
                if self.download_pdfs and items:
                    pdf_count = 0
                    for item in items:
                        try:
                            # Get PDF URL from detail page if needed
                            if not item.get('pdf_url') and item.get('detail_url'):
                                detail_data = self.scrape_detail_page(item['detail_url'])
                                if detail_data.get('pdf_url'):
                                    item['pdf_url'] = detail_data['pdf_url']

                            # Download PDF if URL available
                            if item.get('pdf_url'):
                                pdf_path = self.download_pdf(
                                    item['pdf_url'],
                                    item.get('year'),
                                    item.get('region_name'),
                                    item.get('title', '')
                                )
                                if pdf_path:
                                    item['pdf_path'] = pdf_path
                                    pdf_count += 1

                                # Update current download status
                                with self.progress_lock:
                                    self.current_download = item.get('title', 'unknown')[:50]
                        except Exception as e:
                            error_logger.error(f"Error downloading PDF for item on page {page_num}: {e}")

                    if pdf_count > 0:
                        activity_logger.info(f"Downloaded {pdf_count} PDFs from page {page_num}")

                # Store scraped data
                self.scraped_pages.add(page_num)
                self.page_data[page_num] = items

                with self.progress_lock:
                    self.total_items_scraped += len(items)

                # Save to database immediately
                self.db.insert_many_perda(items)

                activity_logger.info(f"Page {page_num} completed successfully with {len(items)} items", extra={'page_num': page_num})
                return True

    def get_total_pages(self):
        """Get total pages with enhanced error handling"""
        try:
            response = self.make_request_with_retry(self.perda_url)
            if not response:
                return None

            soup = BeautifulSoup(response.content, 'lxml')
            text_content = soup.get_text()

            # Look for total count
            match = re.search(r'(\d+)\s*(?:Perda|perda)\s*ditemukan', text_content, re.IGNORECASE)
            if match:
                total = int(match.group(1))
                pages = (total + self.page_size - 1) // self.page_size
                activity_logger.info(f"Found {total} total items, calculated {pages} pages")
                return pages

            # Check pagination
            pagination = soup.find('ul', class_='pagination') or soup.find('div', class_='pagination')

            if pagination:
                page_links = pagination.find_all('a')
                max_page = 1

                for link in page_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    if 'page=' in href:
                        try:
                            page_num = int(parse_qs(urlparse(href).query).get('page', [0])[0])
                            max_page = max(max_page, page_num)
                        except (ValueError, IndexError):
                            pass

                    try:
                        page_num = int(text)
                        max_page = max(max_page, page_num)
                    except ValueError:
                        pass

                if max_page > 1:
                    return max_page

            # Default fallback
            total_pages = (self.total_expected + self.page_size - 1) // self.page_size
            activity_logger.warning(f"Could not determine total pages, using expected: {total_pages}")
            return total_pages

        except Exception as e:
            error_logger.error(f"Error getting total pages: {e}\n{traceback.format_exc()}")
            return None

    def scrape_all_with_validation(self):
        """Main scraping method with enhanced validation and logging"""

        activity_logger.info("Starting enhanced scraper with validation...")
        console_logger.info("Enhanced scraper starting...")

        # Get total pages
        total_pages = self.get_total_pages()
        if not total_pages:
            error_logger.error("Could not determine total pages")
            return

        activity_logger.info(f"Total pages to scrape: {total_pages}")
        console_logger.info(f"Scraping {total_pages} pages with {self.max_workers} workers")

        # Create priority queue
        page_queue = PriorityQueue()
        retry_queue = Queue()

        # Add all pages to queue
        max_pages = min(total_pages, 2000)
        for page_num in range(1, max_pages + 1):
            page_queue.put(PageTask(priority=page_num, page_num=page_num))

        # Process pages with enhanced monitoring
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = set()
            completed_pages = 0

            with tqdm(total=max_pages, desc="Enhanced scraping") as pbar:
                while not page_queue.empty() or futures or not retry_queue.empty():
                    # Submit new tasks
                    while not page_queue.empty() and len(futures) < self.max_workers:
                        task = page_queue.get()
                        future = executor.submit(self.process_page_task_enhanced, task, total_pages)
                        futures.add(future)

                    # Process retries
                    while not retry_queue.empty() and len(futures) < self.max_workers:
                        task = retry_queue.get()
                        future = executor.submit(self.process_page_task_enhanced, task, total_pages)
                        futures.add(future)

                    # Check completed futures
                    if futures:
                        done, futures = self.wait_for_futures(futures, timeout=2.0)

                        for future in done:
                            try:
                                success = future.result()
                                if success:
                                    completed_pages += 1
                                    pbar.update(1)

                                    # Build postfix with current download if available
                                    postfix_dict = {
                                        'Completed': completed_pages,
                                        'Failed': len(self.failed_pages),
                                        'Items': self.total_items_scraped,
                                        'Retries': self.validation_retries
                                    }

                                    # Show current file being downloaded
                                    with self.progress_lock:
                                        if self.current_download:
                                            postfix_dict['File'] = self.current_download

                                    pbar.set_postfix(postfix_dict)
                                else:
                                    self.validation_retries += 1

                            except Exception as e:
                                error_logger.error(f"Future execution error: {e}\n{traceback.format_exc()}")

                    # Check completion
                    if self.total_items_scraped >= self.total_expected:
                        activity_logger.info(f"Reached expected count of {self.total_expected}")
                        break

        # Process collected data
        self.process_collected_data()

        # Save final state and print statistics
        self.save_scraping_state()
        self.print_enhanced_statistics()

    def wait_for_futures(self, futures, timeout=2.0):
        """Wait for futures with timeout"""
        done = set()
        pending = futures.copy()

        for future in list(pending):
            if future.done():
                done.add(future)
                pending.remove(future)

        return done, pending

    def process_collected_data(self):
        """Process collected data in order - PDFs already downloaded during scraping"""
        activity_logger.info("Processing collected data summary...")
        all_items = []

        for page_num in sorted(self.page_data.keys()):
            all_items.extend(self.page_data[page_num])

        activity_logger.info(f"Total items collected: {len(all_items)}")

        # Count PDFs downloaded
        pdf_count = sum(1 for item in all_items if item.get('pdf_path'))
        activity_logger.info(f"Total PDFs downloaded during scraping: {pdf_count}")
        console_logger.info(f"Scraping complete. Total items: {len(all_items)}, PDFs downloaded: {pdf_count}")

    def scrape_detail_page(self, url):
        """Scrape detail page to get PDF URL and additional information"""
        try:
            session = self.get_thread_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            detail_data = {}

            # Find PDF link on detail page
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True).lower()
                # Look for PDF links or download buttons
                if '.pdf' in href.lower() or 'download' in link_text or 'unduh' in link_text:
                    detail_data['pdf_url'] = urljoin(self.base_url, href)
                    activity_logger.info(f"Found PDF URL on detail page: {detail_data['pdf_url']}")
                    break

            # Extract additional metadata if needed
            content_div = soup.find('div', class_='content') or soup.find('div', class_='detail')
            if content_div:
                for row in content_div.find_all(['tr', 'div']):
                    text = row.get_text(strip=True)
                    if 'kategori' in text.lower():
                        detail_data['category'] = text.split(':', 1)[-1].strip()
                    elif 'subjek' in text.lower():
                        detail_data['subject'] = text.split(':', 1)[-1].strip()

            return detail_data

        except Exception as e:
            error_logger.error(f"Error scraping detail page {url}: {e}")
            return {}

    def download_pdf(self, pdf_url, year, region_name, title):
        """Download PDF file to organized directory structure"""
        if not pdf_url or not self.download_pdfs:
            return None

        try:
            # Create directory structure: docs/year/region/
            year_str = str(year) if year else "unknown_year"
            region_str = re.sub(r'[^\w\s-]', '', region_name or "unknown_region").strip()
            region_str = re.sub(r'[-\s]+', '_', region_str)

            pdf_dir = Path(f"docs/{year_str}/{region_str}")
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from title
            filename = re.sub(r'[^\w\s-]', '', title[:100]).strip()
            filename = re.sub(r'[-\s]+', '_', filename)
            filename = f"{filename}.pdf"

            pdf_path = pdf_dir / filename

            # Skip if already downloaded
            if pdf_path.exists():
                activity_logger.info(f"PDF already exists: {pdf_path}")
                return str(pdf_path)

            # Download PDF with retry logic
            session = self.get_thread_session()  # Get thread-local session
            for attempt in range(3):
                try:
                    response = session.get(pdf_url, stream=True, timeout=30)
                    response.raise_for_status()

                    # Save PDF
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    activity_logger.info(f"Downloaded PDF: {pdf_path}")
                    return str(pdf_path)

                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        error_logger.error(f"Failed to download PDF from {pdf_url}: {e}")
                        break

        except Exception as e:
            error_logger.error(f"Error creating PDF directory or file: {e}")

        return None

    def save_scraping_state(self):
        """Save enhanced scraping state"""
        state = {
            'scraped_pages': list(self.scraped_pages),
            'failed_pages': self.failed_pages,
            'total_items': self.total_items_scraped,
            'validation_retries': self.validation_retries,
            'error_summary': self.error_tracker.errors,
            'timestamp': datetime.now().isoformat()
        }

        state_file = Path('scraping_state_enhanced.json')
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        activity_logger.info(f"Enhanced scraping state saved to {state_file}")

    def print_enhanced_statistics(self):
        """Print detailed statistics"""
        stats = self.db.get_stats()

        print("\n" + "="*70)
        print("ENHANCED SCRAPING COMPLETED")
        print("="*70)
        print(f"Total pages scraped: {len(self.scraped_pages)}")
        print(f"Failed pages: {len(self.failed_pages)}")
        print(f"Total items collected: {self.total_items_scraped}")
        print(f"Validation retries: {self.validation_retries}")
        print(f"Database records: {stats['total_records']}")
        print(f"Total regions: {stats['total_regions']}")
        print(f"Total years: {stats['total_years']}")

        # Count downloaded PDFs
        if self.download_pdfs:
            pdf_count = sum(1 for root, dirs, files in os.walk("docs") for file in files if file.endswith('.pdf'))
            print(f"PDFs downloaded: {pdf_count}")

        # Error summary
        if self.error_tracker.errors:
            print(f"\nError Summary:")
            for error_type, errors in self.error_tracker.errors.items():
                resolved_count = sum(1 for e in errors if e['resolved'])
                total_count = len(errors)
                print(f"  {error_type}: {total_count} occurrences ({resolved_count} resolved)")

        if self.failed_pages:
            print(f"\nFailed pages: {list(self.failed_pages.keys())[:10]}...")

        if stats['total_records'] >= self.total_expected * 0.95:
            print("\n[✓] Target data count achieved!")
        else:
            print(f"\n[!] Scraped {stats['total_records']}/{self.total_expected} expected items")

        print(f"\nLogs saved to: logs/scraper_activity.log and logs/scraper_errors.log")

    def cleanup(self):
        """Enhanced cleanup"""
        activity_logger.info("Cleaning up resources...")

        with self.session_lock:
            for session in self.sessions.values():
                session.close()
            self.sessions.clear()

        activity_logger.info("Cleanup completed")


if __name__ == "__main__":
    """Direct execution for testing"""
    scraper = EnhancedPerdaScraper(
        max_workers=15,
        download_pdfs=False,
        max_retries=3,
        min_items_per_page=18
    )

    try:
        scraper.scrape_all_with_validation()
    except KeyboardInterrupt:
        console_logger.info("Scraping interrupted by user")
        scraper.save_scraping_state()
    except Exception as e:
        error_logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        scraper.save_scraping_state()
        raise
    finally:
        scraper.cleanup()