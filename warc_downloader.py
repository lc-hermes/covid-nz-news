"""WARC file downloader with caching and retry logic."""

import logging
import os
import time
import urllib.error
import urllib.request
from typing import Optional


class WARCDownloader:
    """Download and cache WARC files from Common Crawl."""

    BASE_URL = "https://data.commoncrawl.org"

    def __init__(
        self,
        cache_dir: str,
        timeout: int = 300,
        retry_attempts: int = 3,
        retry_delay: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize WARC downloader.

        Args:
            cache_dir: Directory to cache WARC files
            timeout: Download timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Base delay between retries in seconds
            logger: Logger instance for logging
        """
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.logger = logger or logging.getLogger("covid_nz_news.downloader")

        os.makedirs(cache_dir, exist_ok=True)

    def download(self, filename: str) -> Optional[str]:
        """
        Download WARC file with caching and streaming.

        Args:
            filename: WARC filename (e.g., 'CC-MAIN-2020-16/CC-MAIN-2020-16-warc00000.12345.warc.gz')

        Returns:
            Path to cached WARC file, or None if download failed
        """
        cache_path = os.path.join(self.cache_dir, filename.replace("/", "_"))

        if self._is_valid_cache(cache_path, filename):
            self.logger.info(f"Using cached: {filename[:60]}...")
            return cache_path

        warc_url = f"{self.BASE_URL}/{filename}"
        self.logger.info(f"Downloading: {warc_url[:80]}...")

        for attempt in range(self.retry_attempts):
            try:
                # Stream download to avoid loading entire file into memory
                with urllib.request.urlopen(warc_url, timeout=self.timeout) as response:
                    content_length = int(response.headers.get("content-length", 0))
                    self.logger.info(f"  Content length: {content_length:,} bytes")

                    # Stream directly to disk in chunks
                    with open(cache_path, "wb") as f:
                        downloaded = 0
                        chunk_size = 8 * 1024 * 1024  # 8MB chunks

                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Progress logging every 10MB
                            if downloaded % (10 * 1024 * 1024) < len(chunk):
                                self.logger.info(f"  Downloaded: {downloaded:,} bytes")

                self._store_cache_metadata(cache_path, filename, downloaded)

                self.logger.info(f"Downloaded {downloaded:,} bytes")
                return cache_path

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Rate limited - respect Retry-After header or use exponential backoff
                    retry_after = e.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_seconds = int(retry_after)
                        except ValueError:
                            wait_seconds = 60
                        self.logger.warning(
                            f"Rate limited (429). Waiting {wait_seconds} seconds (from Retry-After header)..."
                        )
                        time.sleep(wait_seconds)
                    else:
                        # No Retry-After header, use exponential backoff with larger delay
                        delay = self.retry_delay * (2**attempt) * 5  # 5x larger for rate limits
                        self.logger.warning(
                            f"Rate limited (429). Waiting {delay} seconds..."
                        )
                        time.sleep(delay)
                    continue  # Retry after waiting

                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: HTTP {e.code}: {e}"
                )
            except urllib.error.URLError as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: {type(e).__name__}: {e}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: {type(e).__name__}: {e}"
                )

            if attempt < self.retry_attempts - 1:
                delay = self.retry_delay * (2**attempt)
                self.logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        self.logger.error(f"Failed to download {filename} after {self.retry_attempts} attempts")
        return None

    def _is_valid_cache(self, cache_path: str, filename: str) -> bool:
        """Check if cached file exists and is valid."""
        if not os.path.exists(cache_path):
            return False

        meta_path = f"{cache_path}.meta"
        if not os.path.exists(meta_path):
            return False

        try:
            with open(meta_path, "r") as f:
                meta = f.read().strip()
            return meta == filename
        except Exception:
            return False

    def _store_cache_metadata(self, cache_path: str, filename: str, size: int):
        """Store metadata for cached file."""
        meta_path = f"{cache_path}.meta"
        with open(meta_path, "w") as f:
            f.write(filename)

        size_path = f"{cache_path}.size"
        with open(size_path, "w") as f:
            f.write(str(size))
