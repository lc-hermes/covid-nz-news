"""Unit tests for WARCExtractor."""

from unittest.mock import MagicMock, patch

import pytest

from warc_extractor import WARCExtractor


class TestWARCExtractor:
    """Test WARC extractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create a WARCExtractor instance."""
        return WARCExtractor(
            min_text_length=100,
            max_content_length=50000,
            allowed_languages=["en"],
            logger=MagicMock(),
        )

    def test_extractor_initialization(self, extractor):
        """Extractor should initialize with correct defaults."""
        assert extractor.min_text_length == 100
        assert extractor.max_content_length == 50000
        assert extractor.allowed_languages == ["en"]

    def test_extract_from_file_returns_list(self, extractor):
        """Extract from file should return a list."""
        # Test with empty target URLs
        result = extractor.extract_from_file("/fake/path/file.warc.gz", set())
        assert isinstance(result, list)

    def test_extract_from_file_empty_file(self, extractor):
        """Extract from empty file should return empty list."""
        with patch("gzip.open", MagicMock()) as mock_gzip:
            mock_file = MagicMock()
            mock_file.__iter__.return_value = iter([])
            mock_gzip.return_value.__enter__.return_value = mock_file

            result = extractor.extract_from_file("/fake/path/empty.warc.gz", set())
            assert isinstance(result, list)

    def test_extract_article_returns_none_for_non_html(self, extractor):
        """Extract article should return None for non-HTML content."""
        from warcio import StatusAndHeaders

        mock_record = MagicMock()
        mock_record.headers = StatusAndHeaders("WARC/1.0", [("Content-Type", "text/plain")])

        headers = {
            "WARC-Target-URI": "https://example.com",
            "WARC-Date": "2020-04-01T00:00:00.000Z",
        }
        result = extractor._extract_article(mock_record, headers)
        assert result is None
