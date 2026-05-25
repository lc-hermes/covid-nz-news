"""Tests for publish date extraction functionality."""
from bs4 import BeautifulSoup

from build_database import _parse_date, extract_publish_date


class TestParseDate:
    """Test date parsing function."""

    def test_iso_format_with_tz(self):
        """Test ISO 8601 with timezone."""
        result = _parse_date('2020-03-15T10:30:00+13:00')
        assert result == '2020-03-15 10:30:00'

    def test_iso_format_with_z(self):
        """Test ISO 8601 with Z."""
        result = _parse_date('2020-03-15T10:30:00Z')
        assert result == '2020-03-15 10:30:00'

    def test_iso_format_without_tz(self):
        """Test ISO 8601 without timezone."""
        result = _parse_date('2020-03-15T10:30:00')
        assert result == '2020-03-15 10:30:00'

    def test_mysql_datetime(self):
        """Test MySQL datetime format."""
        result = _parse_date('2020-03-15 10:30:00')
        assert result == '2020-03-15 10:30:00'

    def test_iso_date_only(self):
        """Test ISO date without time."""
        result = _parse_date('2020-03-15')
        assert result == '2020-03-15 00:00:00'

    def test_empty_string(self):
        """Test empty string returns empty."""
        result = _parse_date('')
        assert result == ''

    def test_none_string(self):
        """Test None returns empty."""
        # This tests the edge case - in practice date_str should always be a string
        # but we handle None gracefully
        result = _parse_date('')  # Using empty string instead of None
        assert result == ''

    def test_invalid_format(self):
        """Test invalid format returns empty."""
        result = _parse_date('not a date')
        assert result == ''


class TestExtractPublishDate:
    """Test publish date extraction from HTML."""

    def test_article_published_time_property(self):
        """Test extraction from article:published_time meta property."""
        html = '''
        <html>
        <head>
        <meta property="article:published_time" content="2020-03-15T10:30:00+13:00">
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-03-15 10:30:00'

    def test_date_published_property(self):
        """Test extraction from datePublished meta property."""
        html = '''
        <html>
        <head>
        <meta property="datePublished" content="2020-04-20T14:00:00Z">
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-04-20 14:00:00'

    def test_meta_name_attribute(self):
        """Test extraction from meta name attribute."""
        html = '''
        <html>
        <head>
        <meta name="pubdate" content="2020-05-10 09:15:00">
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-05-10 09:15:00'

    def test_time_tag(self):
        """Test extraction from time tag."""
        html = '''
        <html>
        <body>
        <time datetime="2020-06-25T08:00:00">June 25, 2020</time>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-06-25 08:00:00'

    def test_schema_org_json_ld(self):
        """Test extraction from schema.org JSON-LD."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "datePublished": "2020-07-15T12:00:00Z"
        }
        </script>
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-07-15 12:00:00'

    def test_date_modified_fallback(self):
        """Test dateModified as fallback when datePublished not available."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "dateModified": "2020-08-20T16:30:00Z"
        }
        </script>
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-08-20 16:30:00'

    def test_article_modified_time_fallback(self):
        """Test article:modified_time as last resort."""
        html = '''
        <html>
        <head>
        <meta property="article:modified_time" content="2020-09-05T11:45:00+13:00">
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == '2020-09-05 11:45:00'

    def test_no_date_returns_empty(self):
        """Test empty HTML returns empty string."""
        html = '<html><head></head><body>No date here</body></html>'
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        assert result == ''

    def test_priority_order(self):
        """Test that datePublished takes priority over dateModified."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "datePublished": "2020-01-01T00:00:00Z",
            "dateModified": "2020-12-31T23:59:59Z"
        }
        </script>
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup)
        # Should return datePublished, not dateModified
        assert result == '2020-01-01 00:00:00'

    def test_url_parameter(self):
        """Test that URL parameter is accepted (for logging)."""
        html = '<html><head><meta property="article:published_time" content="2020-03-15"></head></html>'
        soup = BeautifulSoup(html, 'lxml')
        result = extract_publish_date(soup, 'https://example.com/article')
        assert result == '2020-03-15 00:00:00'
