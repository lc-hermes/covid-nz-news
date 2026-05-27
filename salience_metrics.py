"""Salience metrics for COVID NZ News database.

Calculates various salience metrics from the news database.
"""

import logging
from typing import Optional

import polars as pl

from delta_database import DeltaNewsDatabase


class SalienceMetrics:
    """Calculate salience metrics from the news database."""

    def __init__(self, db: DeltaNewsDatabase, logger: Optional[logging.Logger] = None):
        """
        Initialize with database connection.

        Args:
            db: DeltaNewsDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger or logging.getLogger("covid_nz_news.salience")

    def get_articles_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by day.

        Returns:
            Polars DataFrame with columns: date, article_count
        """
        df = self.db.table.read_polars()

        if df.height == 0:
            return pl.DataFrame({"date": [], "article_count": []})

        # Use timestamp or publish_date for date extraction
        df = df.with_columns(
            pl.when(pl.col("publish_date").is_not_null())
            .then(pl.col("publish_date").str.slice(0, 10))
            .otherwise(pl.col("timestamp").str.slice(0, 10))
            .alias("date")
        )

        result = df.group_by("date").agg(pl.col("date").count().alias("article_count"))
        return result.sort("date")

    def get_articles_per_source(self) -> pl.DataFrame:
        """
        Get article counts grouped by source domain.

        Returns:
            Polars DataFrame with columns: source_domain, article_count
        """
        df = self.db.table.read_polars()

        if df.height == 0:
            return pl.DataFrame({"source_domain": [], "article_count": []})

        result = df.group_by("source_domain").agg(
            pl.col("source_domain").count().alias("article_count")
        )
        return result.sort("article_count", descending=True)

    def get_articles_per_source_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by source and day.

        Returns:
            Polars DataFrame with columns: date, source_domain, article_count
        """
        df = self.db.table.read_polars()

        if df.height == 0:
            return pl.DataFrame({"date": [], "source_domain": [], "article_count": []})

        # Use timestamp or publish_date for date extraction
        df = df.with_columns(
            pl.when(pl.col("publish_date").is_not_null())
            .then(pl.col("publish_date").str.slice(0, 10))
            .otherwise(pl.col("timestamp").str.slice(0, 10))
            .alias("date")
        )

        result = (
            df.group_by("date", "source_domain")
            .agg(pl.col("date").count().alias("article_count"))
            .sort(["date", "source_domain"])
        )
        return result

    def get_total_statistics(self) -> dict:
        """
        Get overall database statistics.

        Returns:
            Dictionary with total articles, date range, sources, etc.
        """
        df = self.db.table.read_polars()

        if df.height == 0:
            return {
                "total_articles": 0,
                "unique_sources": 0,
                "date_earliest": None,
                "date_latest": None,
                "days_covered": 0,
            }

        # Use timestamp or publish_date for date extraction
        df = df.with_columns(
            pl.when(pl.col("publish_date").is_not_null())
            .then(pl.col("publish_date").str.slice(0, 10))
            .otherwise(pl.col("timestamp").str.slice(0, 10))
            .alias("date")
        )

        earliest = df["date"].min()
        latest = df["date"].max()

        from datetime import datetime

        date_earliest = datetime.strptime(str(earliest), "%Y-%m-%d") if earliest else None
        date_latest = datetime.strptime(str(latest), "%Y-%m-%d") if latest else None

        days_covered = (
            (date_latest - date_earliest).days + 1 if date_earliest and date_latest else 0
        )

        return {
            "total_articles": df.height,
            "unique_sources": df["source_domain"].n_unique(),
            "date_earliest": str(earliest) if earliest else None,
            "date_latest": str(latest) if latest else None,
            "days_covered": days_covered,
        }
