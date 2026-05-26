"""Async CDX server client with rate limiting."""

import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp


class AsyncCDXClient:
    """Async client for querying CDX server with rate limiting."""

    def __init__(
        self,
        base_url: str = "https://index.commoncrawl.org/collection-CC-MAIN-2020-{crawl_id}/url.{format}",
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
    ) -> List[str]:
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
            List of matching URLs
        """
        urls = []
        semaphore = await self._get_semaphore()

        async with semaphore:
            for attempt in range(self.max_retries):
                try:
                    self.logger.debug(
                        f"Querying CDX for {domain} in {crawl_id} (attempt {attempt + 1})"
                    )

                    url = self.base_url.format(crawl_id=crawl_id, format="gz")
                    query = f"URL:{domain}"

                    # Add date range parameters if provided
                    params = {"url": query, "fl": "URL", "limit": limit}
                    if date_start:
                        params["from"] = date_start
                    if date_end:
                        params["to"] = date_end

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url,
                            params=params,
                            headers={"Accept-Encoding": "gzip"},
                            timeout=30,
                        ) as response:
                            if response.status == 200:
                                text = await response.text()
                                candidate_urls = [
                                    line.strip()
                                    for line in text.strip().split("\n")
                                    if line.strip()
                                ]

                                # Filter by keywords
                                " ".join(keywords).lower()
                                for url in candidate_urls:
                                    if any(kw in url.lower() for kw in keywords):
                                        urls.append(url)
                                        if len(urls) >= limit:
                                            break

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

        return urls

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
            Dict mapping (domain, crawl_id) -> list of URLs
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

            for (domain, crawl_id), urls in zip(batch, batch_results, strict=False):
                results[(domain, crawl_id)] = urls
                if urls:
                    self.logger.info(f"Found {len(urls)} URLs for {domain} in {crawl_id}")

        return results

    def query_index(
        self,
        crawl_id: str,
        domain_pattern: str,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> List[Dict]:
        """
        Sync wrapper for async query - for compatibility.

        This is a blocking call that runs the async method.
        """
        # This is a simplified version - in production, we'd want to query all at once
        # For now, just return empty list as placeholder
        self.logger.warning("query_index not implemented for async client")
        return []

    def filter_keywords(self, urls: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filter URLs by keywords."""
        return [url for url in urls if any(kw in url.get("url", "").lower() for kw in keywords)]

    def group_by_warc(self, urls: List[Dict]) -> Dict[str, List[Dict]]:
        """Group URLs by WARC file."""
        # Simplified - just return all URLs in one group
        return {"all_urls": urls}
