"""Unit tests for COVID NZ News Database Builder."""

import os

import pytest

from settings import settings


class TestNewsSourceConfig:
    """Test news source configuration."""

    def test_domains_not_empty(self):
        """Ensure at least one domain is configured."""
        assert len(settings.news_sources.domains) > 0

    def test_domains_are_valid_patterns(self):
        """All domains should be valid wildcard patterns."""
        for domain in settings.news_sources.domains:
            assert domain.startswith("*") or domain.startswith("http")
            assert "/" in domain

    def test_keywords_not_empty(self):
        """Ensure at least one COVID keyword is configured."""
        assert len(settings.news_sources.keywords) > 0

    def test_keywords_are_strings(self):
        """All keywords should be strings."""
        for keyword in settings.news_sources.keywords:
            assert isinstance(keyword, str)
            assert len(keyword) > 0


class TestCrawlConfig:
    """Test crawl configuration."""

    def test_crawl_ids_not_empty(self):
        """Ensure at least one crawl ID is configured."""
        assert len(settings.crawls.crawl_ids) > 0

    def test_crawl_ids_are_valid(self):
        """All crawl IDs should follow CC-MAIN-YYYY-N format."""
        import re

        pattern = r"^CC-MAIN-\d{4}-\d+$"
        for crawl_id in settings.crawls.crawl_ids:
            assert re.match(pattern, crawl_id), f"Invalid crawl ID: {crawl_id}"

    def test_crawl_ids_are_unique(self):
        """All crawl IDs should be unique."""
        assert len(settings.crawls.crawl_ids) == len(set(settings.crawls.crawl_ids))


class TestDatabaseConfig:
    """Test database configuration."""

    def test_database_path_is_valid(self):
        """Database path should be a valid path (SQLite .db or Delta Lake directory)."""
        # Accept SQLite (.db) or Delta Lake directory paths
        assert settings.database.path.endswith(".db") or "/" in settings.database.path or "." not in settings.database.path

    def test_cache_directory_exists_or_creatable(self):
        """Cache directory should exist or be creatable."""
        # This test might fail in CI if permissions are restricted
        try:
            os.makedirs(settings.cache.directory, exist_ok=True)
            assert os.path.isdir(settings.cache.directory)
        except PermissionError:
            pytest.skip("Cannot create cache directory in this environment")


class TestNetworkConfig:
    """Test network configuration."""

    def test_timeouts_are_positive(self):
        """All timeouts should be positive integers."""
        assert settings.network.cdx_timeout > 0
        assert settings.network.warc_timeout > 0

    def test_retry_attempts_is_positive(self):
        """Retry attempts should be a positive integer."""
        assert settings.network.retry_attempts > 0

    def test_retry_delay_is_positive(self):
        """Retry delay should be a positive float."""
        assert settings.network.retry_delay > 0


class TestExtractionConfig:
    """Test extraction configuration."""

    def test_max_content_length_is_positive(self):
        """Max content length should be positive."""
        assert settings.extraction.max_content_length > 0

    def test_min_text_length_is_positive(self):
        """Min text length should be positive."""
        assert settings.extraction.min_text_length > 0

    def test_min_text_less_than_max(self):
        """Min text length should be less than max content length."""
        assert settings.extraction.min_text_length < settings.extraction.max_content_length

    def test_allowed_languages_not_empty(self):
        """At least one language should be allowed."""
        assert len(settings.extraction.allowed_languages) > 0


class TestLoggingConfig:
    """Test logging configuration."""

    def test_log_level_is_valid(self):
        """Log level should be a valid Python logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.logging.level in valid_levels

    def test_log_file_has_valid_extension(self):
        """Log file should have .log extension or be empty."""
        if settings.logging.file:
            assert settings.logging.file.endswith(".log") or "/" in settings.logging.file
