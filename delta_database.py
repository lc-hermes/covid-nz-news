"""Delta Lake + Polars database operations for COVID NZ News."""

import hashlib
import logging
import re
from typing import Dict, List, Optional, Tuple

import polars as pl
from deltalake import DeltaTable, write_deltalake


class DeltaNewsDatabase:
    """Delta Lake database for storing news articles using Polars."""

    def __init__(self, table_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize Delta Lake table connection.

        Args:
            table_path: Path to Delta Lake table directory
            logger: Logger instance
        """
        self.table_path = table_path
        self.logger = logger or logging.getLogger("covid_nz_news.delta")
        self._table: Optional[DeltaTable] = None

    @property
    def table(self) -> DeltaTable:
        """Get or create DeltaTable instance."""
        if self._table is None:
            self._table = DeltaTable(self.table_path)
        return self._table

    def _read_table(self) -> pl.DataFrame:  # type: ignore[return-value]
        """Read the Delta table into a Polars DataFrame."""
        return pl.scan_delta(self.table_path).collect()  # type: ignore[return-value]

    def init_table(self):
        """Initialize Delta Lake table with schema if not exists."""
        try:
            # Try to load existing table
            _ = DeltaTable(self.table_path)
            self.logger.info(f"Loaded existing Delta table: {self.table_path}")
        except Exception:
            # Create new table with schema
            schema_df = pl.DataFrame({
                "url": pl.Series([], dtype=pl.Utf8),
                "title": pl.Series([], dtype=pl.Utf8),
                "content": pl.Series([], dtype=pl.Utf8),
                "content_hash": pl.Series([], dtype=pl.Utf8),
                "source_domain": pl.Series([], dtype=pl.Utf8),
                "crawl_id": pl.Series([], dtype=pl.Utf8),
                "timestamp": pl.Series([], dtype=pl.Utf8),
                "language": pl.Series([], dtype=pl.Utf8),
                "status_code": pl.Series([], dtype=pl.Utf8),
                "publish_date": pl.Series([], dtype=pl.Utf8),
            })
            write_deltalake(
                self.table_path,
                schema_df,
                mode="overwrite",
                partition_by=["source_domain"],  # Partition by source for efficient filtering
            )
            self._table = None  # Reset to reload
            self.logger.info(f"Created new Delta table: {self.table_path}")

    def _compute_content_hash(self, content: str) -> str:
        """Compute MD5 hash of normalized content for deduplication."""
        normalized = re.sub(r"\s+", " ", content.lower()).strip()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

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
        Insert an article with deduplication.
        
        NOTE: For better performance, use insert_batch() for multiple articles.
        This method reads the entire table for deduplication check.

        Args:
            All article fields

        Returns:
            True if inserted, False if duplicate
        """
        content_hash = self._compute_content_hash(content)

        # Check for existing content hash
        df = self._read_table()
        existing = df.filter(pl.col("content_hash") == content_hash)
        if existing.height > 0:
            self.logger.debug(f"Skipping duplicate content: {url}")
            return False

        # Create single-row DataFrame
        new_article = pl.DataFrame({
            "url": [url],
            "title": [title],
            "content": [content],
            "content_hash": [content_hash],
            "source_domain": [source_domain],
            "crawl_id": [crawl_id],
            "timestamp": [timestamp],
            "language": [language],
            "status_code": [status_code],
            "publish_date": [publish_date],
        })

        # Append to Delta table
        write_deltalake(self.table_path, new_article, mode="append")
        self._table = None  # Reset to reload with new data
        return True

    def insert_batch(self, articles: List[Dict]) -> int:
        """
        Insert multiple articles with deduplication.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of articles inserted
        """
        if not articles:
            return 0

        # Load existing content hashes for deduplication
        df = self._read_table()
        existing_hashes = set(df.select("content_hash").to_dict(as_series=False)["content_hash"])

        # Filter out duplicates and compute hashes
        new_articles = []
        for article in articles:
            content_hash = self._compute_content_hash(article.get("content", ""))
            if content_hash not in existing_hashes:
                article["content_hash"] = content_hash
                new_articles.append(article)
                existing_hashes.add(content_hash)

        if not new_articles:
            self.logger.debug("All articles were duplicates")
            return 0

        # Convert to Polars DataFrame
        df_new = pl.DataFrame(new_articles)

        # Append to Delta table
        write_deltalake(self.table_path, df_new, mode="append")
        self._table = None  # Reset to reload with new data

        self.logger.info(f"Inserted {len(new_articles)} articles, skipped {len(articles) - len(new_articles)} duplicates")
        return len(new_articles)

    def get_count(self) -> int:
        """Get total article count."""
        df = self._read_table()
        return df.height

    def get_stats_by_source(self) -> List[Tuple[str, int]]:
        """Get article counts grouped by source domain."""
        df = self._read_table()
        result = df.group_by("source_domain").agg(
            pl.col("url").count().alias("count")
        ).sort("count", descending=True)
        return list(result.iter_rows())

    def get_stats_by_language(self) -> List[Tuple[str, int]]:
        """Get article counts grouped by language."""
        df = self._read_table()
        result = df.group_by("language").agg(
            pl.col("url").count().alias("count")
        ).sort("count", descending=True)
        return list(result.iter_rows())

    def query_articles(
        self,
        where: Optional[str] = None,
        params: Optional[Tuple] = None,
        order_by: str = "timestamp DESC",
        limit: int = 100,
    ) -> Dict[str, List]:
        """
        Query articles with filters.

        Args:
            where: WHERE clause (without 'WHERE' keyword) - currently not used, use filters directly
            params: Parameters for WHERE clause - currently not used
            order_by: ORDER BY clause (e.g., "timestamp DESC", "publish_date ASC")
            limit: Maximum results to return

        Returns:
            Dictionary of article data
        """
        df = self._read_table()

        # Apply ordering
        if order_by:
            parts = order_by.split()
            column = parts[0]
            descending = len(parts) > 1 and parts[1].upper() == "DESC"
            df = df.sort(column, descending=descending)

        # Apply limit
        df = df.limit(limit)

        # Convert to dict
        return df.to_dict(as_series=False)

    def get_recent_articles(self, limit: int = 10) -> Dict[str, List]:
        """Get most recent articles by timestamp."""
        return self.query_articles(order_by="timestamp DESC", limit=limit)

    def search_by_keyword(self, keyword: str, limit: int = 50) -> Dict[str, List]:
        """Search articles by keyword in title or content."""
        df = self._read_table()

        # Filter by keyword in title or content
        mask = (
            pl.col("title").str.contains(keyword, literal=False) |
            pl.col("content").str.contains(keyword, literal=False)
        )
        df = df.filter(mask).limit(limit)

        return df.to_dict(as_series=False)

    def query_all_articles(self, columns: Optional[List[str]] = None) -> Dict[str, List]:
        """
        Query all articles from the database.

        Args:
            columns: Optional list of columns to return

        Returns:
            Dictionary of all article data
        """
        df = self._read_table()

        if columns:
            df = df.select(columns)

        return df.to_dict(as_series=False)

    def get_articles_by_date_range(
        self,
        start_date: str,
        end_date: str,
        limit: int = 1000,
    ) -> Dict[str, List]:
        """
        Query articles by publish date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum results

        Returns:
            Dictionary of article data
        """
        df = self._read_table()

        # Filter by date range
        mask = (
            pl.col("publish_date") >= start_date
        ) & (
            pl.col("publish_date") <= end_date
        )
        df = df.filter(mask).limit(limit)

        return df.to_dict(as_series=False)

    def optimize(self):
        """Optimize the Delta table (compact small files, vacuum)."""
        table = DeltaTable(self.table_path)
        table.optimize.compact()
        self.logger.info("Delta table optimized")

    def vacuum(self, retention_hours: int = 24) -> List[str]:
        """
        Remove old files from Delta table.

        Args:
            retention_hours: Hours of history to retain

        Returns:
            List of removed files
        """
        table = DeltaTable(self.table_path)
        removed = table.vacuum(retention_hours, dry_run=False)
        self.logger.info(f"Vacuumed {len(removed) if removed else 0} files from Delta table")
        return removed if removed else []

    def version(self) -> int:
        """Get current Delta table version."""
        return self.table.version()

    def history(self, limit: int = 10) -> List[Dict]:
        """Get Delta table history."""
        return self.table.history(limit)
