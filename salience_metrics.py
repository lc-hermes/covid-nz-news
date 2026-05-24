"""Salience metrics calculation for COVID NZ News database.

Computes article counts over time to measure COVID salience in NZ media.
Uses Polars for efficient data processing.
"""
from datetime import datetime

import polars as pl

from database import NewsDatabase


class SalienceMetrics:
    """Calculate salience metrics from COVID news database."""

    def __init__(self, db: NewsDatabase):
        """
        Initialize salience metrics calculator.

        Args:
            db: NewsDatabase instance
        """
        self.db = db

    def get_articles_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by publish date.

        Returns:
            Polars DataFrame with columns: date, article_count
        """
        # Query all articles with their crawl dates
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({'date': [], 'article_count': []})

        # Convert to Polars DataFrame
        df = pl.DataFrame(articles)

        # Extract date from crawl_date (format: YYYY-MM-DDTHH:MM:SS)
        df = df.with_columns(
            pl.col('crawl_date').str.slice(0, 10).alias('date')
        )

        # Group by date and count
        daily_counts = df.group_by('date').agg(
            pl.len().alias('article_count')
        ).sort('date')

        return daily_counts

    def get_articles_per_source(self) -> pl.DataFrame:
        """
        Get article counts grouped by source domain.

        Returns:
            Polars DataFrame with columns: source_domain, article_count
        """
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({'source_domain': [], 'article_count': []})

        # Convert to Polars DataFrame
        df = pl.DataFrame(articles)

        # Group by source and count
        source_counts = df.group_by('source_domain').agg(
            pl.len().alias('article_count')
        ).sort('article_count', descending=True)

        return source_counts

    def get_articles_per_source_per_day(self) -> pl.DataFrame:
        """
        Get article counts grouped by source and date.

        Returns:
            Polars DataFrame with columns: date, source_domain, article_count
        """
        articles = self.db.query_all_articles()

        if not articles:
            return pl.DataFrame({
                'date': [],
                'source_domain': [],
                'article_count': []
            })

        # Convert to Polars DataFrame
        df = pl.DataFrame(articles)

        # Extract date from crawl_date
        df = df.with_columns(
            pl.col('crawl_date').str.slice(0, 10).alias('date')
        )

        # Group by date and source, count
        daily_source_counts = df.group_by(['date', 'source_domain']).agg(
            pl.len().alias('article_count')
        ).sort(['date', 'article_count'])

        return daily_source_counts

    def get_total_statistics(self) -> dict:
        """
        Get overall statistics about the database.

        Returns:
            Dictionary with total articles, unique sources, date range
        """
        articles = self.db.query_all_articles()

        if not articles:
            return {
                'total_articles': 0,
                'unique_sources': 0,
                'earliest_date': None,
                'latest_date': None,
                'date_range_days': 0
            }

        # Convert to Polars DataFrame
        df = pl.DataFrame(articles)

        # Extract date from crawl_date
        df = df.with_columns(
            pl.col('crawl_date').str.slice(0, 10).alias('date')
        )

        # Calculate statistics
        total = len(df)
        sources = df['source_domain'].n_unique()
        earliest = df['date'].min()
        latest = df['date'].max()

        # Calculate date range in days
        if earliest and latest:
            date_earliest = datetime.strptime(earliest, '%Y-%m-%d')
            date_latest = datetime.strptime(latest, '%Y-%m-%d')
            date_range = (date_latest - date_earliest).days
        else:
            date_range = 0

        return {
            'total_articles': total,
            'unique_sources': sources,
            'earliest_date': earliest,
            'latest_date': latest,
            'date_range_days': date_range
        }

    def export_to_csv(
        self,
        output_path: str,
        include_daily: bool = True,
        include_source: bool = True,
        include_daily_source: bool = False
    ) -> None:
        """
        Export salience metrics to CSV files.

        Args:
            output_path: Base path for output files (without extension)
            include_daily: Include daily article counts
            include_source: Include per-source counts
            include_daily_source: Include per-source per-day counts
        """
        if include_daily:
            daily_df = self.get_articles_per_day()
            daily_df.write_csv(f"{output_path}_daily.csv")

        if include_source:
            source_df = self.get_articles_per_source()
            source_df.write_csv(f"{output_path}_by_source.csv")

        if include_daily_source:
            daily_source_df = self.get_articles_per_source_per_day()
            daily_source_df.write_csv(f"{output_path}_daily_by_source.csv")

    def print_summary(self) -> None:
        """Print a summary of salience metrics to console."""
        stats = self.get_total_statistics()

        print("\n" + "=" * 60)
        print("COVID NZ News Salience Metrics Summary")
        print("=" * 60)
        print(f"Total articles: {stats['total_articles']:,}")
        print(f"Unique sources: {stats['unique_sources']}")
        print(f"Date range: {stats['earliest_date']} to {stats['latest_date']}")
        print(f"Days covered: {stats['date_range_days']}")

        if stats['total_articles'] > 0 and stats['date_range_days'] > 0:
            avg_per_day = stats['total_articles'] / stats['date_range_days']
            print(f"Average articles per day: {avg_per_day:.2f}")

        print("\nArticles by Source:")
        print("-" * 40)
        source_df = self.get_articles_per_source()
        for row in source_df.iter_rows():
            print(f"  {row[0]}: {row[1]:,}")

        print("\n" + "=" * 60)
