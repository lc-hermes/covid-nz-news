"""Unit tests for salience metrics calculation."""

import logging
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from delta_database import DeltaNewsDatabase
from salience_metrics import SalienceMetrics


class TestSalienceMetrics:
    """Test salience metrics functionality."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary Delta Lake table."""
        db_path = tmp_path / "test_delta"
        db = DeltaNewsDatabase(str(db_path), MagicMock())
        db.init_table()
        
        # Insert test data
        db.insert_article(
            url="https://example.com/article1",
            title="Test Article 1",
            content="Test content 1",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-03-15T10:00:00",
            language="en",
            status_code="200",
            publish_date="2020-03-15",
        )
        db.insert_article(
            url="https://example.com/article2",
            title="Test Article 2",
            content="Test content 2",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-03-15T11:00:00",
            language="en",
            status_code="200",
            publish_date="2020-03-15",
        )
        db.insert_article(
            url="https://other.com/article3",
            title="Test Article 3",
            content="Test content 3",
            source_domain="other.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-03-16T10:00:00",
            language="en",
            status_code="200",
            publish_date="2020-03-16",
        )
        
        return db

    @pytest.fixture
    def metrics(self, db):
        """Create a SalienceMetrics instance."""
        return SalienceMetrics(db, MagicMock())

    def test_get_articles_per_day(self, metrics):
        """Should return daily article counts."""
        result = metrics.get_articles_per_day()

        assert isinstance(result, pl.DataFrame)
        assert "publish_date" in result.columns
        assert "article_count" in result.columns
        assert len(result) == 2  # Two unique dates

        # Check first day has 2 articles
        first_day_count = result.filter(pl.col("publish_date") == "2020-03-15")["article_count"][0]
        assert first_day_count == 2

    def test_get_articles_per_source(self, metrics):
        """Should return article counts per source."""
        result = metrics.get_articles_per_source()

        assert isinstance(result, pl.DataFrame)
        assert "source_domain" in result.columns
        assert "article_count" in result.columns
        assert len(result) == 2  # Two unique sources

        # Check example.com has 2 articles
        example_count = result.filter(pl.col("source_domain") == "example.com")["article_count"][0]
        assert example_count == 2

    def test_get_articles_per_source_per_day(self, metrics):
        """Should return article counts per source per day."""
        result = metrics.get_articles_per_source_per_day()

        assert isinstance(result, pl.DataFrame)
        assert "publish_date" in result.columns
        assert "source_domain" in result.columns
        assert "article_count" in result.columns
        assert len(result) == 2  # Two unique source-date combinations

    def test_empty_database(self, tmp_path):
        """Should handle empty database gracefully."""
        db_path = tmp_path / "empty_delta"
        db = DeltaNewsDatabase(str(db_path), MagicMock())
        db.init_table()
        
        metrics = SalienceMetrics(db, MagicMock())

        daily = metrics.get_articles_per_day()
        assert len(daily) == 0

        source = metrics.get_articles_per_source()
        assert len(source) == 0

        daily_source = metrics.get_articles_per_source_per_day()
        assert len(daily_source) == 0
