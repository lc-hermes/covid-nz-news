"""Unit tests for CDXClient."""

from unittest.mock import MagicMock, patch

import pytest

from cdx_client import CDXClient


class TestCDXClient:
    """Test CDX client functionality."""

    @pytest.fixture
    def client(self):
        """Create a CDXClient instance."""
        return CDXClient(timeout=30, retry_attempts=2, retry_delay=0.1, logger=MagicMock())

    def test_query_index_returns_list(self, client):
        """Query index should return a list."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"example.com/2020/04/01 https://example.com/article"
            mock_urlopen.return_value = mock_response

            result = client.query_index("CC-MAIN-2020-16", "*.example.com/")
            assert isinstance(result, list)

    def test_filter_keywords_filters_correctly(self, client):
        """Filter keywords should return only URLs containing keywords."""
        urls = [
            {"url": "https://example.com/covid-article"},
            {"url": "https://example.com/other-article"},
            {"url": "https://example.com/coronavirus-news"},
        ]
        keywords = ["covid", "coronavirus"]

        result = client.filter_keywords(urls, keywords)
        assert len(result) == 2
        assert all("covid" in u["url"] or "coronavirus" in u["url"] for u in result)

    def test_filter_keywords_case_insensitive(self, client):
        """Keyword filtering should be case-insensitive."""
        urls = [
            {"url": "https://example.com/COVID-article"},
            {"url": "https://example.com/cOvId-news"},
        ]
        keywords = ["covid"]

        result = client.filter_keywords(urls, keywords)
        assert len(result) == 2

    def test_filter_keywords_empty_keywords(self, client):
        """Empty keywords should return empty list."""
        urls = [
            {"url": "https://example.com/article"},
        ]
        keywords = []

        result = client.filter_keywords(urls, keywords)
        assert len(result) == 0

    def test_group_by_warc_groups_correctly(self, client):
        """Group by WARC should group URLs by their WARC file."""
        urls = [
            {"url": "https://example.com/1", "filename": "warc1.warc.gz"},
            {"url": "https://example.com/2", "filename": "warc1.warc.gz"},
            {"url": "https://example.com/3", "filename": "warc2.warc.gz"},
        ]

        result = client.group_by_warc(urls)
        assert len(result) == 2
        assert len(result["warc1.warc.gz"]) == 2
        assert len(result["warc2.warc.gz"]) == 1

    def test_group_by_warc_empty_input(self, client):
        """Empty input should return empty dict."""
        result = client.group_by_warc([])
        assert isinstance(result, dict)
        assert len(result) == 0
