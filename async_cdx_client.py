"""Async CDX server client with rate limiting."""

import asyncio
import json
import logging
from typing import Dict, List, Optional

import aiohttp


class AsyncCDXClient:
    """Async client for querying CDX server with rate limiting."""

    def __init__(
        self,
        base_url: str = "https://index.commoncrawl.org/{crawl_id}-index?url={query}",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: float = 10.0,  # requests per second
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize async CDX client.

        Args:
            base_url: Base URL for CDX server
            max_retries: Maximum retry attempts
            retry_delay: Initial delay between retries (seconds)
            rate_limit: Maximum requests per second
            logger: Logger instance
        """
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit = rate_limit
        self.logger = logger or logging.getLogger("covid_nz_news.async_cdx")
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create rate limit semaphore."""
        if self._semaphore is None:
            # Limit to rate_limit requests at a time
            self._semaphore = asyncio.Semaphore(max(1, int(self.rate_limit)))
        return self._semaphore

    async def query_urls(
        self,
        crawl_id: str,
        domain: str,
        keywords: List[str],
        limit: int = 500,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query CDX server for URLs matching domain and keywords.

        Args:
            crawl_id: Common Crawl crawl ID
            domain: Target domain
            keywords: List of keywords to search for
            limit: Maximum URLs to return
            date_start: Optional start date filter (ISO format, e.g., '2020-04-01')
            date_end: Optional end date filter (ISO format, e.g., '2020-06-30')

        Returns:
            List of URL entries with metadata (url, filename, timestamp, offset)
        """
        entries = []
        semaphore = await self._get_semaphore()

        async with semaphore:
            for attempt in range(self.max_retries):
                try:
                    self.logger.debug(
                        f"Querying CDX for {domain} in {crawl_id} (attempt {attempt + 1})"
                    )

                    # Build query URL with parameters
                    params_str = f"limit={limit}&output=json"
                    if date_start:
                        params_str += f"&from={date_start}"
                    if date_end:
                        params_str += f"&to={date_end}"

                    url = self.base_url.format(crawl_id=crawl_id, query=f"{domain}&{params_str}")

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=120),
                        ) as response:
                            if response.status == 200:
                                text = await response.text()
                                # Parse JSON lines from CDX response
                                candidate_urls = []
                                for line in text.strip().split("\n"):
                                    if line.strip():
                                        try:
                                            entry = json.loads(line)
                                            url = entry.get("url", "")
                                            if url:
                                                # Store full entry with metadata (filename for WARC download)
                                                candidate_urls.append({
                                                    "url": url,
                                                    "filename": entry.get("filename", ""),
                                                    "timestamp": entry.get("timestamp", ""),
                                                    "offset": entry.get("offset", ""),
                                                })
                                        except json.JSONDecodeError:
                                            continue

                                # Filter by keywords (skip if no keywords provided)
                                if keywords:
                                    filtered = []
                                    for entry in candidate_urls:
                                        if any(kw in entry["url"].lower() for kw in keywords):
                                            filtered.append(entry)
                                            if len(filtered) >= limit:
                                                break
                                    urls = filtered
                                else:
                                    # No keyword filter - return all entries up to limit
                                    urls = candidate_urls[:limit]

                                if urls:
                                    self.logger.debug(f"Found {len(urls)} URLs for {domain}")
                                    return urls

                            elif response.status == 404:
                                self.logger.warning(f"No CDX data for {crawl_id}")
                                return []
                            else:
                                self.logger.error(f"CDX query failed: {response.status}")

                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout querying CDX for {domain} in {crawl_id}")
                except aiohttp.ClientError as e:
                    self.logger.error(f"Client error querying CDX: {type(e).__name__}: {e}")
                except Exception as e:
                    self.logger.error(f"Error querying CDX: {type(e).__name__}: {e}")

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.debug(f"Retrying in {delay}s")
                    await asyncio.sleep(delay)

        return entries

    async def query_all_urls(
        self,
        domains: List[str],
        crawls: List[str],
        keywords: List[str],
        limit_per_domain: int = 500,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> dict:
        """
        Query all domain-crawl combinations in parallel.

        Args:
            domains: List of target domains
            crawls: List of crawl IDs
            keywords: List of keywords
            limit_per_domain: Max URLs per domain-crawl pair
            date_start: Optional start date filter (ISO format)
            date_end: Optional end date filter (ISO format)

        Returns:
            Dict mapping (domain, crawl_id) -> list of URL entries
        """
        results = {}
        tasks = []

        for domain in domains:
            for crawl_id in crawls:
                task = self.query_urls(
                    crawl_id, domain, keywords, limit_per_domain, date_start, date_end
                )
                tasks.append(((domain, crawl_id), task))

        # Process in batches to avoid overwhelming the server
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_results = await asyncio.gather(*[task for _, task in batch])

            for (domain, crawl_id), entries in zip(batch, batch_results, strict=False):
                results[(domain, crawl_id)] = entries
                if entries:
                    self.logger.info(f"Found {len(entries)} URLs for {domain} in {crawl_id}")

        return results

    def query_index(
        self,
        crawl_id: str,
        domain_pattern: str,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> List[Dict]:
        """
        Sync wrapper for async query - for compatibility with sync client.

        Queries all URLs for a domain pattern without keyword filtering.
        """
        # Run the async query without keywords to get all URLs
        import asyncio

        async def _query():
            # Use empty keywords to get all URLs
            entries = await self.query_urls(
                crawl_id, domain_pattern, keywords=[], limit=10000,
                date_start=date_start, date_end=date_end
            )
            # Return entries as-is (they already have the right format)
            return entries

        return asyncio.run(_query())

    def filter_keywords_url_only(self, urls: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Filter URLs by keywords (URL-only filtering).
        
        DEPRECATED: Use filter_keywords_content_based for better recall.
        This method only checks URL paths, missing articles where keywords appear in content only.
        """
        return [url for url in urls if any(kw in url.get("url", "").lower() for kw in keywords)]
    
    def filter_keywords_content_based(self, urls: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Filter URLs by keywords (content-based filtering).
        
        This method downloads ALL URLs from the WARC files, then filters based on
        the actual content of the page. This significantly improves recall compared
        to URL-only filtering, as it catches articles where keywords appear in the
        body text but not in the URL path.
        
        Args:
            urls: List of URL entries from CDX query
            keywords: List of keywords to search for in page content
            
        Returns:
            Filtered list of URLs where keywords appear in the page content
        """
        from warc_extractor import extract_content_from_url  # type: ignore
        
        filtered_urls = []
        for url_entry in urls:
            url = url_entry.get("url", "")
            try:
                # Extract content from WARC
                content = extract_content_from_url(url)
                # Check if any keyword appears in the content
                if content and any(kw.lower() in content.lower() for kw in keywords):
                    filtered_urls.append(url_entry)
            except Exception as e:
                self.logger.debug(f"Failed to extract content from {url}: {e}")
                # Skip this URL if extraction fails
        
        self.logger.info(f"Content-based filtering: {len(filtered_urls)}/{len(urls)} URLs matched keywords")
        return filtered_urls
    
    def filter_keywords(self, urls: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        DEPRECATED: Renamed to filter_keywords_url_only.
        This method only checks URL paths, missing articles where keywords appear in content only.
        Use filter_keywords_content_based for better recall.
        """
        return self.filter_keywords_url_only(urls, keywords)

    def group_by_warc(self, urls: List[Dict]) -> Dict[str, List[Dict]]:
        """Group URLs by WARC file."""
        warc_groups: Dict[str, List[Dict]] = {}
        for url_entry in urls:
            # Extract the full WARC filename from the CDX record
            warc_key = url_entry.get("filename", "")
            if warc_key:
                if warc_key not in warc_groups:
                    warc_groups[warc_key] = []
                warc_groups[warc_key].append(url_entry)
        return warc_groups
