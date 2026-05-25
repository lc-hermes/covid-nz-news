"""Database operations for COVID NZ News."""

import logging
import sqlite3
from typing import Dict, List, Optional, Tuple


class NewsDatabase:
    """SQLite database for storing news articles."""

    def __init__(self, db_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
            logger: Logger instance
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger("covid_nz_news.db")
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish database connection and create schema."""
        self.conn = sqlite3.connect(self.db_path)
        self._create_schema()
        self.logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _get_cursor(self) -> sqlite3.Cursor:
        """Get database cursor, raising error if not connected."""
        if self.conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.conn.cursor()

    def _create_schema(self):
        """Create database schema if not exists."""
        cursor = self._get_cursor()

        # Create articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                content_hash TEXT,
                source_domain TEXT,
                crawl_id TEXT,
                timestamp TEXT,
                language TEXT,
                status_code TEXT,
                publish_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source_domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON articles(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language ON articles(language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_publish_date ON articles(publish_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON articles(content_hash)")

        if self.conn:
            self.conn.commit()
        self.logger.info("Database schema created/verified")

    def insert_article(
        self,
        url: str,
        title: str,
        content: str,
        source_domain: str,
        crawl_id: str,
        timestamp: str,
        language: str,
        status_code: str,
        publish_date: str = "",
    ) -> bool:
        """
        Insert or replace an article.

        Args:
            All article fields

        Returns:
            True if successful, False otherwise
        """
        cursor = self._get_cursor()

        try:
            # Compute content hash for deduplication
            # Normalize content to handle near-duplicates (whitespace, case)
            import hashlib
            import re

            normalized = re.sub(r"\s+", " ", content.lower()).strip()
            content_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()

            # Check if content already exists
            cursor.execute("SELECT id FROM articles WHERE content_hash = ?", (content_hash,))
            if cursor.fetchone():
                self.logger.debug(f"Skipping duplicate content: {url}")
                return False

            cursor.execute(
                """
                INSERT OR REPLACE INTO articles
                (url, title, content, content_hash, source_domain, crawl_id, timestamp, language, status_code, publish_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    url,
                    title,
                    content,
                    content_hash,
                    source_domain,
                    crawl_id,
                    timestamp,
                    language,
                    status_code,
                    publish_date,
                ),
            )
            if self.conn:
                self.conn.commit()
            return True

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error inserting {url}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inserting {url}: {type(e).__name__}: {e}")
            return False

    def get_count(self) -> int:
        """Get total article count."""
        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        return cursor.fetchone()[0]

    def get_stats_by_source(self) -> List[Tuple[str, int]]:
        """Get article counts grouped by source domain."""
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT source_domain, COUNT(*) FROM articles GROUP BY source_domain ORDER BY COUNT(*) DESC"
        )
        return cursor.fetchall()

    def get_stats_by_language(self) -> List[Tuple[str, int]]:
        """Get article counts grouped by language."""
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT language, COUNT(*) FROM articles GROUP BY language ORDER BY COUNT(*) DESC"
        )
        return cursor.fetchall()

    def query_articles(
        self,
        where: Optional[str] = None,
        params: Optional[Tuple] = None,
        order_by: str = "timestamp DESC",
        limit: int = 100,
    ) -> List[Dict]:
        """
        Query articles with filters.

        Args:
            where: WHERE clause (without 'WHERE' keyword)
            params: Parameters for WHERE clause
            order_by: ORDER BY clause
            limit: Maximum results to return

        Returns:
            List of article dictionaries
        """
        cursor = self._get_cursor()

        query = "SELECT id, url, title, content, source_domain, crawl_id, timestamp, language, status_code, created_at FROM articles"

        if where:
            query += f" WHERE {where}"

        query += f" ORDER BY {order_by} LIMIT {limit}"

        cursor.execute(query, params or ())

        columns = [
            "id",
            "url",
            "title",
            "content",
            "source_domain",
            "crawl_id",
            "timestamp",
            "language",
            "status_code",
            "created_at",
        ]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

    def get_recent_articles(self, limit: int = 10) -> List[Dict]:
        """Get most recent articles."""
        return self.query_articles(order_by="timestamp DESC", limit=limit)

    def search_by_keyword(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search articles by keyword in title or content."""
        search_param = f"%{keyword}%"
        return self.query_articles(
            where="(title LIKE ? OR content LIKE ?)",
            params=(search_param, search_param),
            limit=limit,
        )

    def query_all_articles(self) -> List[Dict]:
        """
        Query all articles from the database.

        Returns:
            List of all article dictionaries
        """
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT url, title, content, source_domain, language, status_code, timestamp FROM articles"
        )
        columns = [
            "url",
            "title",
            "content",
            "source_domain",
            "language",
            "status_code",
            "crawl_date",
        ]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
