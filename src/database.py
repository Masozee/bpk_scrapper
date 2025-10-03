import sqlite3
from datetime import datetime
from pathlib import Path
import logging
import shutil

logger = logging.getLogger(__name__)

class PerdaDatabase:
    def __init__(self, db_path='database/perda.db', worker_id=None):
        if worker_id is not None:
            # Per-worker database
            base_path = Path(db_path)
            self.db_path = base_path.parent / f"{base_path.stem}_worker_{worker_id}{base_path.suffix}"
            self.is_worker_db = True
            self.worker_id = worker_id
        else:
            # Main database
            self.db_path = Path(db_path)
            self.is_worker_db = False
            self.worker_id = None

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.init_database()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self):
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0  # Wait up to 30 seconds for lock
        )
        self.connection.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        self.connection.execute('PRAGMA journal_mode=WAL')
        return self.connection
    
    def close(self):
        if self.connection:
            self.connection.close()
    
    def init_database(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS perda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    number TEXT,
                    year INTEGER,
                    region_name TEXT,
                    region_type TEXT,
                    region_code TEXT,
                    category TEXT,
                    subject TEXT,
                    status TEXT,
                    source TEXT,
                    detail_url TEXT UNIQUE,
                    pdf_url TEXT,
                    pdf_path TEXT,
                    description TEXT,
                    enacted_date DATE,
                    published_date DATE,
                    metadata JSON,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_perda_year ON perda(year)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_perda_region ON perda(region_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_perda_detail_url ON perda(detail_url)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_perda_source ON perda(source)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraping_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_number INTEGER,
                    items_count INTEGER,
                    status TEXT,
                    error_message TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def insert_perda(self, data):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO perda (
                    title, number, year, region_name, region_type, region_code,
                    category, subject, status, source, detail_url, pdf_url,
                    pdf_path, description, enacted_date, published_date, metadata,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('title'),
                data.get('number'),
                data.get('year'),
                data.get('region_name'),
                data.get('region_type'),
                data.get('region_code'),
                data.get('category'),
                data.get('subject'),
                data.get('status'),
                data.get('source'),
                data.get('detail_url'),
                data.get('pdf_url'),
                data.get('pdf_path'),
                data.get('description'),
                data.get('enacted_date'),
                data.get('published_date'),
                data.get('metadata'),
                datetime.now().isoformat()
            ))
            
            return cursor.lastrowid
    
    def insert_many_perda(self, data_list):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            prepared_data = [
                (
                    data.get('title'),
                    data.get('number'),
                    data.get('year'),
                    data.get('region_name'),
                    data.get('region_type'),
                    data.get('region_code'),
                    data.get('category'),
                    data.get('subject'),
                    data.get('status'),
                    data.get('source'),
                    data.get('detail_url'),
                    data.get('pdf_url'),
                    data.get('pdf_path'),
                    data.get('description'),
                    data.get('enacted_date'),
                    data.get('published_date'),
                    data.get('metadata'),
                    datetime.now().isoformat()
                )
                for data in data_list
            ]
            
            cursor.executemany('''
                INSERT OR REPLACE INTO perda (
                    title, number, year, region_name, region_type, region_code,
                    category, subject, status, source, detail_url, pdf_url,
                    pdf_path, description, enacted_date, published_date, metadata,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', prepared_data)
            
            return cursor.rowcount
    
    def log_scraping(self, page_number, items_count, status='success', error_message=None):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scraping_log (page_number, items_count, status, error_message)
                VALUES (?, ?, ?, ?)
            ''', (page_number, items_count, status, error_message))
    
    def get_total_count(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM perda')
            return cursor.fetchone()[0]
    
    def get_perda_by_url(self, detail_url):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM perda WHERE detail_url = ?', (detail_url,))
            return cursor.fetchone()
    
    def get_stats(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM perda')
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT region_name) FROM perda')
            stats['total_regions'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT year) FROM perda')
            stats['total_years'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM perda WHERE pdf_path IS NOT NULL')
            stats['pdfs_downloaded'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT region_name, COUNT(*) as count 
                FROM perda 
                GROUP BY region_name 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            stats['top_regions'] = cursor.fetchall()
            
            cursor.execute('''
                SELECT year, COUNT(*) as count
                FROM perda
                WHERE year IS NOT NULL
                GROUP BY year
                ORDER BY year DESC
                LIMIT 10
            ''')
            stats['recent_years'] = cursor.fetchall()

            return stats

    @staticmethod
    def merge_worker_databases(main_db_path='database/perda.db'):
        """Merge all worker databases into the main database"""
        main_db_path = Path(main_db_path)
        worker_dbs = list(main_db_path.parent.glob(f"{main_db_path.stem}_worker_*{main_db_path.suffix}"))

        if not worker_dbs:
            logger.info("No worker databases found to merge")
            return 0

        logger.info(f"Found {len(worker_dbs)} worker databases to merge")

        # Connect to main database
        main_conn = sqlite3.connect(main_db_path, timeout=30.0)
        main_conn.execute('PRAGMA journal_mode=WAL')
        main_cursor = main_conn.cursor()

        total_merged = 0

        for worker_db in worker_dbs:
            try:
                logger.info(f"Merging {worker_db.name}...")

                # Attach worker database
                main_cursor.execute(f"ATTACH DATABASE '{worker_db}' AS worker")

                # Merge perda table
                main_cursor.execute('''
                    INSERT OR REPLACE INTO perda
                    SELECT * FROM worker.perda
                ''')
                rows_merged = main_cursor.rowcount
                total_merged += rows_merged

                # Merge scraping_log table
                main_cursor.execute('''
                    INSERT INTO scraping_log
                    SELECT * FROM worker.scraping_log
                ''')

                # Detach worker database
                main_cursor.execute("DETACH DATABASE worker")

                main_conn.commit()

                logger.info(f"Merged {rows_merged} records from {worker_db.name}")

                # Delete worker database after successful merge
                worker_db.unlink()
                # Also delete WAL and SHM files if they exist
                for ext in ['-wal', '-shm']:
                    wal_file = worker_db.parent / f"{worker_db.name}{ext}"
                    if wal_file.exists():
                        wal_file.unlink()

            except Exception as e:
                logger.error(f"Error merging {worker_db.name}: {e}")
                # Detach if still attached
                try:
                    main_cursor.execute("DETACH DATABASE worker")
                except:
                    pass

        main_conn.close()

        logger.info(f"Merge complete: {total_merged} total records merged from {len(worker_dbs)} workers")
        return total_merged