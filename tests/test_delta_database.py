"""Unit tests for Delta Lake database operations."""

from unittest.mock import MagicMock

import pytest

from delta_database import DeltaNewsDatabase


class TestDeltaNewsDatabase:
    """Test Delta Lake database operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary Delta Lake table."""
        db_path = tmp_path / "test_delta"
        db = DeltaNewsDatabase(str(db_path), MagicMock())
        db.init_table()
        yield db

    def test_insert_article(self, db):
        """Insert article should add to database."""
        result = db.insert_article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        assert result is True
        assert db.get_count() == 1

    def test_insert_duplicate_content(self, db):
        """Insert duplicate content should be skipped."""
        result1 = db.insert_article(
            url="https://example.com/article",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        assert result1 is True
        assert db.get_count() == 1

        # Second insert with same content should be skipped
        result2 = db.insert_article(
            url="https://example.com/article2",
            title="Test 2",
            content="Content",  # Same content
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-02",
            language="en",
            status_code="200",
        )
        assert result2 is False
        # Count should still be 1 (duplicate content)
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
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        assert db.get_count() == 1

    def test_get_stats_by_source(self, db):
        """Get stats by source should return grouped counts."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content from example",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://other.com/1",
            title="Test",
            content="Content from other",
            source_domain="other.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )

        stats = db.get_stats_by_source()
        assert len(stats) == 2
        # Stats returns List[Tuple[source_domain, count]]
        source_counts = {s[0]: s[1] for s in stats}
        assert source_counts["example.com"] == 1
        assert source_counts["other.com"] == 1

    def test_get_stats_by_language(self, db):
        """Get stats by language should return grouped counts."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="English content here",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://example.com/2",
            title="Test",
            content="French content ici",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="fr",
            status_code="200",
        )

        stats = db.get_stats_by_language()
        assert len(stats) == 2
        # Stats returns List[Tuple[language, count]]
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
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )

        articles = db.get_recent_articles(limit=1)
        # Returns Dict[str, List]
        assert len(articles["url"]) == 1
        assert articles["url"][0] == "https://example.com/1"

    def test_search_by_keyword(self, db):
        """Search by keyword should return matching articles."""
        db.insert_article(
            url="https://example.com/1",
            title="COVID Article",
            content="This is about COVID-19",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://example.com/2",
            title="Other Article",
            content="This is about something else",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )

        articles = db.search_by_keyword("COVID", limit=10)
        # Returns Dict[str, List]
        assert len(articles["url"]) == 1
        assert "COVID" in articles["title"][0] or "COVID" in articles["content"][0]

    def test_query_articles(self, db):
        """Query articles should return filtered results."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )

        articles = db.query_articles(order_by="timestamp DESC", limit=10)
        # Returns Dict[str, List]
        assert len(articles["url"]) == 1

    def test_content_hash_deduplication(self, db):
        """Duplicate content should be detected and skipped."""
        # Insert first article
        result1 = db.insert_article(
            url="https://example.com/article1",
            title="Test Article",
            content="This is the same content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        assert result1 is True
        assert db.get_count() == 1

        # Try to insert duplicate content with different URL
        result2 = db.insert_article(
            url="https://example.com/article2",
            title="Test Article 2",
            content="This is the same content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-02",
            language="en",
            status_code="200",
        )
        # Should return False because content is duplicate
        assert result2 is False
        # Count should still be 1
        assert db.get_count() == 1

    def test_query_all_articles(self, db):
        """Query all articles should return all inserted articles."""
        db.insert_article(
            url="https://example.com/1",
            title="Test 1",
            content="Content 1",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        db.insert_article(
            url="https://example.com/2",
            title="Test 2",
            content="Content 2",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-02",
            language="en",
            status_code="200",
        )

        articles = db.query_all_articles()
        # Returns Dict[str, List]
        assert len(articles["url"]) == 2

    def test_get_urls(self, db):
        """Get URLs should return list of URLs."""
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )

        articles = db.query_all_articles(columns=["url"])
        assert "https://example.com/1" in articles["url"]

    def test_get_url_count(self, db):
        """Get URL count should return correct count."""
        assert db.get_count() == 0
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        assert db.get_count() == 1

    def test_is_url_exists(self, db):
        """Check if URL exists should return correct boolean."""
        articles = db.query_all_articles(columns=["url"])
        assert "https://example.com/1" not in articles["url"]
        
        db.insert_article(
            url="https://example.com/1",
            title="Test",
            content="Content",
            source_domain="example.com",
            crawl_id="CC-MAIN-2020-16",
            timestamp="2020-04-01",
            language="en",
            status_code="200",
        )
        
        articles = db.query_all_articles(columns=["url"])
        assert "https://example.com/1" in articles["url"]
