#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Scraper - Abstract base class for all scrapers
Provides common functionality and interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import requests
from fake_useragent import UserAgent
from threading import Lock, RLock
import threading
import logging
from pathlib import Path
import json
import time
import random
from datetime import datetime

# Setup logging
activity_logger = logging.getLogger('activity')
error_logger = logging.getLogger('errors')


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


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""

    def __init__(self, source_name: str, base_url: str, max_workers: int = 15,
                 download_pdfs: bool = True, max_retries: int = 5,
                 min_items_per_page: int = 18):
        """
        Initialize base scraper

        Args:
            source_name: Identifier for this scraper (e.g., 'peraturan_go_id', 'bpk')
            base_url: Base URL for the website
            max_workers: Number of concurrent workers
            download_pdfs: Whether to download PDF files
            max_retries: Maximum retry attempts per page
            min_items_per_page: Minimum expected items per page
        """
        self.source_name = source_name
        self.base_url = base_url
        self.max_workers = max_workers
        self.download_pdfs = download_pdfs
        self.max_retries = max_retries
        self.min_items_per_page = min_items_per_page

        # Session management
        self.session_lock = RLock()
        self.sessions = {}
        self.ua = UserAgent()

        # Data structures
        self.data_lock = Lock()
        self.scraped_pages = set()
        self.failed_pages = {}
        self.page_data = {}

        # Progress tracking
        self.progress_lock = Lock()
        self.total_items_scraped = 0
        self.validation_retries = 0

        # Error tracking
        self.error_tracker = ErrorTracker()

        # State file
        self.state_file = Path(f'scraping_state_{source_name}.json')

        # Setup logging for this source
        self._setup_source_logging()

    def _setup_source_logging(self):
        """Setup source-specific logging"""
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)

        # Activity logger
        self.activity_logger = logging.getLogger(f'activity.{self.source_name}')
        self.activity_logger.setLevel(logging.INFO)

        if not self.activity_logger.handlers:
            handler = logging.FileHandler(logs_dir / f'{self.source_name}_activity.log', encoding='utf-8')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
            ))
            self.activity_logger.addHandler(handler)

        # Error logger
        self.error_logger = logging.getLogger(f'errors.{self.source_name}')
        self.error_logger.setLevel(logging.WARNING)

        if not self.error_logger.handlers:
            handler = logging.FileHandler(logs_dir / f'{self.source_name}_errors.log', encoding='utf-8')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n'
            ))
            self.error_logger.addHandler(handler)

    def get_session(self) -> requests.Session:
        """Get or create a thread-local session"""
        thread_id = threading.get_ident()

        with self.session_lock:
            if thread_id not in self.sessions:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': self.ua.random,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                })
                self.sessions[thread_id] = session

            return self.sessions[thread_id]

    def save_scraping_state(self):
        """Save current scraping state to file"""
        state = {
            'scraped_pages': list(self.scraped_pages),
            'failed_pages': self.failed_pages,
            'total_items': self.total_items_scraped,
            'timestamp': datetime.now().isoformat()
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

        self.activity_logger.info(f"State saved to {self.state_file}")

    def load_scraping_state(self) -> bool:
        """Load previous scraping state if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                self.scraped_pages = set(state.get('scraped_pages', []))
                self.failed_pages = state.get('failed_pages', {})
                self.total_items_scraped = state.get('total_items', 0)

                self.activity_logger.info(f"Loaded state: {len(self.scraped_pages)} pages scraped")
                return True
            except Exception as e:
                self.error_logger.error(f"Failed to load state: {e}")

        return False

    def cleanup(self):
        """Cleanup resources"""
        with self.session_lock:
            for session in self.sessions.values():
                session.close()
            self.sessions.clear()

    # Abstract methods that subclasses must implement
    @abstractmethod
    def get_total_pages(self) -> int:
        """Get total number of pages to scrape"""
        pass

    @abstractmethod
    def parse_page(self, page_num: int) -> List[Dict]:
        """Parse a single page and return list of items"""
        pass

    @abstractmethod
    def scrape_all_with_validation(self):
        """Main scraping method with validation logic"""
        pass