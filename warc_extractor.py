"""WARC file extractor with streaming support."""
import gzip
import logging
from typing import Dict, List, Optional, Set

import langdetect
from bs4 import BeautifulSoup
from warcio import ArchiveIterator


class WARCExtractor:
    """Extract articles from WARC files with streaming support."""

    def __init__(
        self,
        max_content_length: int = 50000,
        min_text_length: int = 100,
        allowed_languages: Optional[List[str]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize WARC extractor.

        Args:
            max_content_length: Maximum content length to store
            min_text_length: Minimum text length for valid articles
            allowed_languages: List of allowed language codes
            logger: Logger instance
        """
        self.max_content_length = max_content_length
        self.min_text_length = min_text_length
        self.allowed_languages = allowed_languages or ['en']
        self.logger = logger or logging.getLogger('covid_nz_news.extractor')

    def extract_from_file(
        self,
        warc_path: str,
        target_urls: Set[str]
    ) -> List[Dict]:
        """
        Extract articles from a WARC file for specific URLs.

        Uses streaming to avoid loading entire file into memory.

        Args:
            warc_path: Path to gzipped WARC file
            target_urls: Set of URLs to extract

        Returns:
            List of extracted article dictionaries
        """
        extracted = []

        self.logger.info(f"Extracting from {warc_path[:60]}...")
        self.logger.info(f"Looking for {len(target_urls)} target URLs")

        # Stream decompression and parsing
        try:
            with gzip.open(warc_path, 'rb') as gz_file:
                reader = ArchiveIterator(gz_file)

                for record in reader:
                    headers = dict(record.rec_headers.headers)

                    record_type = headers.get('WARC-Type', '')
                    record_url = headers.get('WARC-Target-URI', '')

                    # Only process response records for our target URLs
                    if record_type == 'response' and record_url in target_urls:
                        article = self._extract_article(record, headers)
                        if article:
                            extracted.append(article)

        except gzip.BadGzipFile:
            self.logger.error(f"Invalid gzip file: {warc_path}")
        except Exception as e:
            self.logger.error(f"Failed to process WARC file: {type(e).__name__}: {e}")

        self.logger.info(f"Extracted {len(extracted)} articles")
        return extracted

    def _extract_article(self, record, headers: Dict) -> Optional[Dict]:
        """
        Extract a single article from a WARC record.

        Args:
            record: WARC record object
            headers: Record headers dictionary

        Returns:
            Article dictionary or None if extraction failed
        """
        url = headers.get('WARC-Target-URI', '')

        try:
            # Read payload
            payload = record.raw_stream.read()
            content = payload.decode('utf-8', errors='ignore')

            # Parse HTML
            soup = BeautifulSoup(content, 'lxml')

            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            # Extract main text
            text = self._extract_main_text(soup)

            # Validate text length
            if len(text) < self.min_text_length:
                self.logger.debug(f"Skipping {url}: text too short ({len(text)} chars)")
                return None

            # Detect language
            try:
                lang = langdetect.detect(text[:10000])
            except langdetect.LangDetectException:
                lang = 'unknown'

            # Filter by language
            if lang not in self.allowed_languages:
                self.logger.debug(f"Skipping {url}: language {lang} not allowed")
                return None

            return {
                'url': url,
                'title': title,
                'content': text[:self.max_content_length],
                'language': lang,
                'status_code': headers.get('WARC-Status-Code', ''),
            }

        except Exception as e:
            self.logger.error(f"Failed to extract {url}: {type(e).__name__}: {e}")
            return None

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """
        Extract main article text from HTML.

        Uses heuristics to find the most likely article content.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted text content
        """
        # Remove unwanted elements
        for elem in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            elem.decompose()

        # Try main tag
        main = soup.find('main')
        if main:
            text = main.get_text(separator=' ', strip=True)
            if len(text) > self.min_text_length:
                return text

        # Try article tag
        article = soup.find('article')
        if article:
            text = article.get_text(separator=' ', strip=True)
            if len(text) > self.min_text_length:
                return text

        # Try common article containers
        for selector in ['div.article', 'div.content', 'div.body', 'div.main']:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(separator=' ', strip=True)
                if len(text) > self.min_text_length:
                    return text

        # Fallback: find longest paragraph block
        paragraphs = soup.find_all(['p', 'div'])
        texts = [p.get_text(separator=' ', strip=True) for p in paragraphs]
        texts = [t for t in texts if len(t) > self.min_text_length]

        if texts:
            return max(texts, key=len)  # type: ignore

        # Last resort: get all text
        return soup.get_text(separator=' ', strip=True)
