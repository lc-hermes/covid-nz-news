"""Unit tests for database operations."""
import pytest
import sqlite3
import tempfile
from unittest.mock import MagicMock
from database import NewsDatabase


class TestNewsDatabase:
    """Test database operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary database."""
        db_path = tmp_path / 'test.db'
        db = NewsDatabase(str(db_path), MagicMock())
        db.connect()
        yield db
        db.close()

    def test_insert_article(self, db):
        """Insert article should add to database."""
        result = db.insert_article(
            url='https://example.com/article',
            title='Test Article',
            content='Test content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        assert result is True
        assert db.get_count() == 1

    def test_insert_duplicate_url(self, db):
        """Insert duplicate URL should update, not fail."""
        result1 = db.insert_article(
            url='https://example.com/article',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        assert result1 is True
        assert db.get_count() == 1
        
        # Second insert with same URL should update (INSERT OR REPLACE)
        result2 = db.insert_article(
            url='https://example.com/article',
            title='Test 2',
            content='Content 2',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200402000000',
            language='en',
            status_code='200'
        )
        assert result2 is True
        # Count should still be 1 (updated, not inserted)
        assert db.get_count() == 1

    def test_get_count(self, db):
        """Get count should return correct count."""
        assert db.get_count() == 0
        db.insert_article(
            url='https://example.com/1',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        assert db.get_count() == 1

    def test_get_stats_by_source(self, db):
        """Get stats by source should return grouped counts."""
        db.insert_article(
            url='https://example.com/1',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        db.insert_article(
            url='https://other.com/1',
            title='Test',
            content='Content',
            source_domain='other.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )

        stats = db.get_stats_by_source()
        assert len(stats) == 2
        source_counts = {s[0]: s[1] for s in stats}
        assert source_counts['example.com'] == 1
        assert source_counts['other.com'] == 1

    def test_get_stats_by_language(self, db):
        """Get stats by language should return grouped counts."""
        db.insert_article(
            url='https://example.com/1',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        db.insert_article(
            url='https://example.com/2',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='fr',
            status_code='200'
        )

        stats = db.get_stats_by_language()
        assert len(stats) == 2
        lang_counts = {s[0]: s[1] for s in stats}
        assert lang_counts['en'] == 1
        assert lang_counts['fr'] == 1

    def test_get_recent_articles(self, db):
        """Get recent articles should return articles."""
        db.insert_article(
            url='https://example.com/1',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )

        articles = db.get_recent_articles(limit=1)
        assert len(articles) == 1
        assert articles[0]['url'] == 'https://example.com/1'

    def test_search_by_keyword(self, db):
        """Search by keyword should return matching articles."""
        db.insert_article(
            url='https://example.com/1',
            title='COVID Article',
            content='This is about COVID-19',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )
        db.insert_article(
            url='https://example.com/2',
            title='Other Article',
            content='This is about something else',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )

        articles = db.search_by_keyword('COVID', limit=10)
        assert len(articles) == 1
        assert 'COVID' in articles[0]['title'] or 'COVID' in articles[0]['content']

    def test_query_articles(self, db):
        """Query articles should return filtered results."""
        db.insert_article(
            url='https://example.com/1',
            title='Test',
            content='Content',
            source_domain='example.com',
            crawl_id='CC-MAIN-2020-16',
            timestamp='20200401000000',
            language='en',
            status_code='200'
        )

        articles = db.query_articles(where='source_domain = ?', params=('example.com',), limit=10)
        assert len(articles) == 1

    def test_close(self, db):
        """Close should close connection."""
        db.close()
        assert db.conn is None
