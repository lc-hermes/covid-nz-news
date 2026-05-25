"""Unit tests for database operations."""

from unittest.mock import MagicMock

import pytest

from database import NewsDatabase


class TestNewsDatabase:
    """Test database operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary database."""
        db_path = tmp_path / "test.db"
        db = NewsDatabase(str(db_path), MagicMock())
        db.connect()
        yield db
        db.close()

    def test_insert_article(self, db):
        """Insert article should add to database."""
        result = db.insert_article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result is True
        assert db.get_count() == 1

    def test_insert_duplicate_url(self, db):
        """Insert duplicate URL should update, not fail."""
        result1 = db.insert_article(
            url="https://example.com/article",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result1 is True
        assert db.get_count() == 1

        # Second insert with same URL should update (INSERT OR REPLACE)
        result2 = db.insert_article(
            url="https://example.com/article",
            title="Test 2",
            content="Content 2",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200402000000",
            language="en",
            status_code="200",
        )
        assert result2 is True
        # Count should still be 1 (updated, not inserted)
        assert db.get_count() == 1

    def test_get_count(self, db):
        """Get count should return correct count."""
        assert db.get_count() == 0
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert db.get_count() == 1

    def test_get_stats_by_source(self, db):
        """Get stats by source should return grouped counts."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content from example",  # Different content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://other.com/1",
            title="Test",
            content="Content from other",  # Different content
            source_domain="other.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )

        stats = db.get_stats_by_source()
        assert len(stats) == 2
        source_counts = {s[0]: s[1] for s in stats}
        assert source_counts["example.com"] == 1
        assert source_counts["other.com"] == 1

    def test_get_stats_by_language(self, db):
        """Get stats by language should return grouped counts."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="English content here",  # Different content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://example.com/2",
            title="Test",
            content="French content ici",  # Different content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="fr",
            status_code="200",
        )

        stats = db.get_stats_by_language()
        assert len(stats) == 2
        lang_counts = {s[0]: s[1] for s in stats}
        assert lang_counts["en"] == 1
        assert lang_counts["fr"] == 1

    def test_get_recent_articles(self, db):
        """Get recent articles should return articles."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )

        articles = db.get_recent_articles(limit=1)
        assert len(articles) == 1
        assert articles[0]["url"] == "https://example.com/1"

    def test_search_by_keyword(self, db):
        """Search by keyword should return matching articles."""
        db.insert_article(
            url="https://example.com/1",
            title="COVID Article",
            content="This is about COVID-19",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://example.com/2",
            title="Other Article",
            content="This is about something else",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )

        articles = db.search_by_keyword("COVID", limit=10)
        assert len(articles) == 1
        assert "COVID" in articles[0]["title"] or "COVID" in articles[0]["content"]

    def test_query_articles(self, db):
        """Query articles should return filtered results."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )

        articles = db.query_articles(where="source_domain = ?", params=("example.com",), limit=10)
        assert len(articles) == 1

    def test_close(self, db):
        """Close should close connection."""
        db.close()
        assert db.conn is None

    def test_content_hash_deduplication(self, db):
        """Duplicate content should be detected and skipped."""
        # Insert first article
        result1 = db.insert_article(
            url="https://example.com/article1",
            title="Test Article",
            content="This is the same content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result1 is True
        assert db.get_count() == 1

        # Try to insert duplicate content with different URL
        result2 = db.insert_article(
            url="https://example.com/article2",  # Different URL
            title="Test Article 2",  # Different title
            content="This is the same content",  # Same content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200402000000",
            language="en",
            status_code="200",
        )
        # Should return False because content is duplicate
        assert result2 is False
        # Count should still be 1
        assert db.get_count() == 1

    def test_whitespace_normalization(self, db):
        """Content with different whitespace should be considered duplicate."""
        # Insert first article
        result1 = db.insert_article(
            url="https://example.com/article1",
            title="Test",
            content="This is content with spaces",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result1 is True

        # Try to insert with extra whitespace (should be duplicate)
        result2 = db.insert_article(
            url="https://example.com/article2",
            title="Test",
            content="This  is  content  with  spaces",  # Extra spaces between same words
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200402000000",
            language="en",
            status_code="200",
        )
        # Should be detected as duplicate due to normalization
        assert result2 is False
        assert db.get_count() == 1

    def test_case_insensitive_deduplication(self, db):
        """Content with different case should be considered duplicate."""
        # Insert first article
        result1 = db.insert_article(
            url="https://example.com/article1",
            title="Test",
            content="This is content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result1 is True

        # Try to insert with different case (should be duplicate)
        result2 = db.insert_article(
            url="https://example.com/article2",
            title="Test",
            content="THIS IS CONTENT",  # Uppercase
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200402000000",
            language="en",
            status_code="200",
        )
        # Should be detected as duplicate due to case normalization
        assert result2 is False
        assert db.get_count() == 1

    def test_different_content_not_deduplicated(self, db):
        """Different content should not be deduplicated."""
        # Insert first article
        result1 = db.insert_article(
            url="https://example.com/article1",
            title="Test",
            content="This is content A",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200401000000",
            language="en",
            status_code="200",
        )
        assert result1 is True

        # Insert different content
        result2 = db.insert_article(
            url="https://example.com/article2",
            title="Test",
            content="This is content B",  # Different content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="20200402000000",
            language="en",
            status_code="200",
        )
        # Should be inserted because content is different
        assert result2 is True
        assert db.get_count() == 2
