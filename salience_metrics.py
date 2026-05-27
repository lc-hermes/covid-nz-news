"""Salience metrics for COVID NZ News articles."""

import logging
from typing import Dict, List, Optional, Tuple

import polars as pl

from delta_database import DeltaNewsDatabase


class SalienceMetrics:
    """Calculate salience metrics for news articles."""

    def __init__(self, db: DeltaNewsDatabase, logger: Optional[logging.Logger] = None):
        """
        Initialize salience metrics calculator.

        Args:
            db: DeltaNewsDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger or logging.getLogger("covid_nz_news.salience")

    def _read_table(self) -> pl.DataFrame:  # type: ignore[return-value]
        """Read the Delta table into a Polars DataFrame."""
        return pl.scan_delta(self.db.table_path).collect()  # type: ignore[return-value]

    def calculate_content_salience(self) -> Dict[str, List]:
        """
        Calculate content salience scores based on article length and recency.

        Returns:
            Dictionary of salience scores
        """
        df = self._read_table()

        if df.height == 0:
            self.logger.warning("No articles found in database")
            return {}

        # Calculate salience based on content length
        df = df.with_columns(
            pl.col("content").str.len().alias("content_length")
        )

        # Return results
        return df.to_dict(as_series=False)

    def get_source_salience(self) -> Dict[str, List]:
        """
        Calculate salience scores by source domain.

        Returns:
            Dictionary of source salience scores
        """
        df = self._read_table()

        if df.height == 0:
            self.logger.warning("No articles found in database")
            return {}

        result = df.group_by("source_domain").agg(
            pl.col("url").count().alias("article_count"),
            pl.col("content").str.len().mean().alias("avg_content_length"),
        ).sort("article_count", descending=True)

        return result.to_dict(as_series=False)

    def get_language_salience(self) -> Dict[str, List]:
        """
        Calculate salience scores by language.

        Returns:
            Dictionary of language salience scores
        """
        df = self._read_table()

        if df.height == 0:
            self.logger.warning("No articles found in database")
            return {}

        df = df.with_columns(
            pl.col("content").str.len().alias("content_length")
        )

        result = df.group_by("language").agg(
            pl.col("url").count().alias("article_count"),
            pl.col("content_length").mean().alias("avg_content_length"),
        ).sort("article_count", descending=True)

        return result.to_dict(as_series=False)

    def get_temporal_salience(self) -> Dict[str, List]:
        """
        Calculate temporal salience scores based on publication dates.

        Returns:
            Dictionary of temporal salience scores
        """
        df = self._read_table()

        if df.height == 0:
            self.logger.warning("No articles found in database")
            return {}

        # Add content length
        df = df.with_columns(
            pl.col("content").str.len().alias("content_length")
        )

        # Group by publish date
        result = df.group_by("publish_date").agg(
            pl.col("url").count().alias("article_count"),
            pl.col("content_length").sum().alias("total_content_length"),
        ).sort("publish_date", descending=True)

        return result.to_dict(as_series=False)

    def get_articles_per_day(self) -> pl.DataFrame:
        """
        Get article counts per day.

        Returns:
            Polars DataFrame with daily counts
        """
        df = self._read_table()
        result = df.group_by("publish_date").agg(
            pl.col("url").count().alias("article_count")
        ).sort("publish_date")
        return result

    def get_articles_per_source(self) -> pl.DataFrame:
        """
        Get article counts per source.

        Returns:
            Polars DataFrame with source counts
        """
        df = self._read_table()
        result = df.group_by("source_domain").agg(
            pl.col("url").count().alias("article_count")
        ).sort("article_count", descending=True)
        return result

    def get_articles_per_source_per_day(self) -> pl.DataFrame:
        """
        Get article counts per source per day.

        Returns:
            Polars DataFrame with source per day counts
        """
        df = self._read_table()
        result = df.group_by(["source_domain", "publish_date"]).agg(
            pl.col("url").count().alias("article_count")
        ).sort(["source_domain", "publish_date"])
        return result

    def get_total_statistics(self) -> Dict[str, int]:
        """
        Get total statistics.

        Returns:
            Dictionary with total counts
        """
        df = self._read_table()
        return {
            "total_articles": df.height,
            "unique_sources": df["source_domain"].n_unique(),
            "unique_languages": df["language"].n_unique(),
        }
