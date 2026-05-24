"""Salience metrics calculation for COVID NZ News database.

Computes article counts over time to measure COVID salience in NZ media.
Uses Polars for efficient data processing.
"""
import logging
from datetime import datetime
from typing import Optional

import polars as pl

from database import NewsDatabase


class SalienceMetrics:
    """Calculate salience metrics from the news database."""

    def __init__(self, db: NewsDatabase, logger: Optional[logging.Logger] = None):
        """
        Initialize with database connection.

        Args:
            db: Connected NewsDatabase instance
            logger: Logger instance
        """
        self.db = db
        self.logger = logger or logging.getLogger('covid_nz_news.salience')

    def get_articles_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by day.

        Returns:
            Polars DataFrame with columns: date, article_count
        """
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({'date': [], 'article_count': []})

        df = pl.DataFrame(articles)
        df = df.with_columns(pl.col('crawl_date').str.slice(0, 10).alias('date'))

        result = df.group_by('date').agg(pl.col('date').count().alias('article_count'))
        return result.sort('date')

    def get_articles_per_source(self) -> pl.DataFrame:
        """
        Get article counts grouped by source domain.

        Returns:
            Polars DataFrame with columns: source_domain, article_count
        """
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({'source_domain': [], 'article_count': []})

        df = pl.DataFrame(articles)
        result = df.group_by('source_domain').agg(pl.col('source_domain').count().alias('article_count'))
        return result.sort('article_count', descending=True)

    def get_articles_per_source_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by source and day.

        Returns:
            Polars DataFrame with columns: date, source_domain, article_count
        """
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({'date': [], 'source_domain': [], 'article_count': []})

        df = pl.DataFrame(articles)
        df = df.with_columns(pl.col('crawl_date').str.slice(0, 10).alias('date'))

        result = (
            df.group_by('date', 'source_domain')
            .agg(pl.col('date').count().alias('article_count'))
            .sort(['date', 'source_domain'])
        )
        return result

    def get_total_statistics(self) -> dict:
        """
        Get overall database statistics.

        Returns:
            Dictionary with total articles, date range, sources, etc.
        """
        articles = self.db.query_all_articles()

        if not articles:
            return {
                'total_articles': 0,
                'unique_sources': 0,
                'date_earliest': None,
                'date_latest': None,
                'days_covered': 0,
            }

        df = pl.DataFrame(articles)
        df = df.with_columns(pl.col('crawl_date').str.slice(0, 10).alias('date'))

        earliest = df['date'].min()
        latest = df['date'].max()

        date_earliest = datetime.strptime(str(earliest), '%Y-%m-%d') if earliest else None
        date_latest = datetime.strptime(str(latest), '%Y-%m-%d') if latest else None

        days_covered = (date_latest - date_earliest).days + 1 if date_earliest and date_latest else 0

        return {
            'total_articles': len(df),
            'unique_sources': df['source_domain'].n_unique(),
            'date_earliest': str(earliest) if earliest else None,
            'date_latest': str(latest) if latest else None,
            'days_covered': days_covered,
        }
