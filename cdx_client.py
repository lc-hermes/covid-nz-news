"""CDX client for querying Common Crawl index."""

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional


class CDXClient:
    """Client for querying Common Crawl CDX index with retry logic."""

    def __init__(
        self,
        timeout: int = 60,
        retry_attempts: int = 3,
        retry_delay: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize CDX client.

        Args:
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Base delay between retries in seconds
            logger: Logger instance for logging
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.logger = logger or logging.getLogger("covid_nz_news.cdx")

    def query_index(
        self, crawl_id: str, domain: str, date_start: Optional[str] = None, date_end: Optional[str] = None
    ) -> List[Dict]:
        """
        Query Common Crawl CDX index for URLs matching domain.

        Args:
            crawl_id: Common Crawl ID (e.g., 'CC-MAIN-2020-16')
            domain: URL pattern to match (e.g., '*.nzherald.co.nz/')
            date_start: Optional start date filter (ISO format, e.g., '2020-04-01')
            date_end: Optional end date filter (ISO format, e.g., '2020-06-30')

        Returns:
            List of URL entries with metadata
        """
        query_url = f"https://index.commoncrawl.org/{crawl_id}-index?url={domain}&output=json"

        # Add date range parameters if provided
        params = {}
        if date_start:
            params["from"] = date_start
        if date_end:
            params["to"] = date_end

        if params:
            query_url += "&" + "&".join(f"{k}={v}" for k, v in params.items())

        self.logger.info(f"Querying CDX index: {query_url[:100]}...")

        for attempt in range(self.retry_attempts):
            try:
                with urllib.request.urlopen(query_url, timeout=self.timeout) as response:
                    data = response.read().decode("utf-8")
                    urls = [json.loads(line) for line in data.strip().split("\n") if line]
                    self.logger.info(f"Found {len(urls)} URLs")
                    return urls

            except urllib.error.URLError as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: {type(e).__name__}: {e}"
                )
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                return []
            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: {type(e).__name__}: {e}"
                )

            if attempt < self.retry_attempts - 1:
                delay = self.retry_delay * (2**attempt)
                self.logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        self.logger.error(f"Failed after {self.retry_attempts} attempts")
        return []

    def filter_keywords(self, urls: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Filter URLs that contain any of the specified keywords.

        Args:
            urls: List of URL entries from CDX query
            keywords: List of keywords to search for

        Returns:
            Filtered list of URLs containing keywords
        """
        covid_urls = []
        for url_entry in urls:
            url = url_entry.get("url", "").lower()
            if any(keyword.lower() in url for keyword in keywords):
                covid_urls.append(url_entry)

        self.logger.info(f"Filtered to {len(covid_urls)} URLs matching keywords")
        return covid_urls

    def group_by_warc(self, urls: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group URLs by their WARC file.

        Args:
            urls: List of URL entries

        Returns:
            Dictionary mapping WARC filename to list of URL entries
        """
        warc_files = {}
        for url_entry in urls:
            filename = url_entry.get("filename", "")
            if filename:
                if filename not in warc_files:
                    warc_files[filename] = []
                warc_files[filename].append(url_entry)

        self.logger.info(f"Grouped into {len(warc_files)} unique WARC files")
        return warc_files
