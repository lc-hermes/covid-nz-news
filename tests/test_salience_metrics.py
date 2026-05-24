"""Unit tests for salience metrics calculation."""
import pytest
import polars as pl
from unittest.mock import MagicMock

from salience_metrics import SalienceMetrics


class TestSalienceMetrics:
    """Test salience metrics functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.query_all_articles.return_value = [
            {
                'url': 'https://example.com/article1',
                'title': 'Test Article 1',
                'content': 'Test content 1',
                'source_domain': 'example.com',
                'language': 'en',
                'status_code': '200',
                'crawl_date': '2020-03-15T10:00:00'
            },
            {
                'url': 'https://example.com/article2',
                'title': 'Test Article 2',
                'content': 'Test content 2',
                'source_domain': 'example.com',
                'language': 'en',
                'status_code': '200',
                'crawl_date': '2020-03-15T11:00:00'
            },
            {
                'url': 'https://other.com/article3',
                'title': 'Test Article 3',
                'content': 'Test content 3',
                'source_domain': 'other.com',
                'language': 'en',
                'status_code': '200',
                'crawl_date': '2020-03-16T10:00:00'
            },
        ]
        return db

    @pytest.fixture
    def metrics(self, mock_db):
        """Create a SalienceMetrics instance."""
        return SalienceMetrics(mock_db)

    def test_get_articles_per_day(self, metrics):
        """Should return daily article counts."""
        result = metrics.get_articles_per_day()

        assert isinstance(result, pl.DataFrame)
        assert 'date' in result.columns
        assert 'article_count' in result.columns
        assert len(result) == 2  # Two unique dates

        # Check first day has 2 articles
        first_day_count = result.filter(pl.col('date') == '2020-03-15')['article_count'][0]
        assert first_day_count == 2

    def test_get_articles_per_source(self, metrics):
        """Should return article counts per source."""
        result = metrics.get_articles_per_source()

        assert isinstance(result, pl.DataFrame)
        assert 'source_domain' in result.columns
        assert 'article_count' in result.columns
        assert len(result) == 2  # Two unique sources

        # Check example.com has 2 articles
        example_count = result.filter(pl.col('source_domain') == 'example.com')['article_count'][0]
        assert example_count == 2

    def test_get_articles_per_source_per_day(self, metrics):
        """Should return article counts per source per day."""
        result = metrics.get_articles_per_source_per_day()

        assert isinstance(result, pl.DataFrame)
        assert 'date' in result.columns
        assert 'source_domain' in result.columns
        assert 'article_count' in result.columns
        assert len(result) == 2  # Two unique source-date combinations

    def test_empty_database(self):
        """Should handle empty database gracefully."""
        mock_db = MagicMock()
        mock_db.query_all_articles.return_value = []

        metrics = SalienceMetrics(mock_db)

        daily = metrics.get_articles_per_day()
        assert len(daily) == 0

        source = metrics.get_articles_per_source()
        assert len(source) == 0

        daily_source = metrics.get_articles_per_source_per_day()
        assert len(daily_source) == 0
