"""Unit tests for WARCDownloader."""

import os
from unittest.mock import MagicMock

import pytest

from warc_downloader import WARCDownloader


class TestWARCDownloader:
    """Test WARC downloader functionality."""

    @pytest.fixture
    def downloader(self, tmp_path):
        """Create a WARCDownloader instance."""
        return WARCDownloader(
            cache_dir=str(tmp_path),
            timeout=30,
            retry_attempts=2,
            retry_delay=0.1,
            logger=MagicMock(),
        )

    def test_downloader_initialization(self, downloader):
        """Downloader should initialize with correct defaults."""
        assert downloader.timeout == 30
        assert downloader.retry_attempts == 2
        assert downloader.retry_delay == 0.1
        assert os.path.isdir(downloader.cache_dir)

    def test_download_returns_cache_path(self, downloader):
        """Download should return cache path."""
        # Create a fake cached file with meta
        filename = "CC-MAIN-2020-16/test.warc.gz"
        cache_path = os.path.join(downloader.cache_dir, "CC-MAIN-2020-16_test.warc.gz")
        with open(cache_path, "w") as f:
            f.write("test")

        # Create meta file
        meta_path = f"{cache_path}.meta"
        with open(meta_path, "w") as f:
            f.write(filename)

        result = downloader.download(filename)
        assert result is not None
        assert result == cache_path

    def test_download_creates_cache_dir(self, downloader):
        """Downloader should create cache directory if it doesn't exist."""
        assert os.path.isdir(downloader.cache_dir)

    def test_download_filename_conversion(self, downloader):
        """Download should convert filename to cache path correctly."""
        filename = "CC-MAIN-2020-16/test.warc.gz"
        expected_cache = os.path.join(downloader.cache_dir, "CC-MAIN-2020-16_test.warc.gz")

        # Create the file and meta
        with open(expected_cache, "w") as f:
            f.write("test")

        meta_path = f"{expected_cache}.meta"
        with open(meta_path, "w") as f:
            f.write(filename)

        result = downloader.download(filename)
        assert result is not None
        assert os.path.basename(result) == "CC-MAIN-2020-16_test.warc.gz"

    def test_download_handles_missing_file(self, downloader):
        """Download should handle missing file gracefully."""
        filename = "CC-MAIN-2020-16/missing.warc.gz"
        # Don't create the file - it will try to download
        # For testing purposes, we just check it doesn't crash
        result = downloader.download(filename)
        # Will return None since file doesn't exist and download will fail
        assert result is None

    def test_is_valid_cache(self, downloader):
        """Valid cache should return True."""
        cache_path = os.path.join(downloader.cache_dir, "test.warc.gz")
        with open(cache_path, "w") as f:
            f.write("test")

        # Create meta file
        meta_path = f"{cache_path}.meta"
        with open(meta_path, "w") as f:
            f.write("test.warc.gz")

        result = downloader._is_valid_cache(cache_path, "test.warc.gz")
        assert result is True

    def test_is_valid_cache_missing_file(self, downloader):
        """Missing cache file should return False."""
        cache_path = os.path.join(downloader.cache_dir, "missing.warc.gz")
        result = downloader._is_valid_cache(cache_path, "missing.warc.gz")
        assert result is False

    def test_is_valid_cache_missing_meta(self, downloader):
        """Cache without meta file should return False."""
        cache_path = os.path.join(downloader.cache_dir, "no_meta.warc.gz")
        with open(cache_path, "w") as f:
            f.write("test")

        result = downloader._is_valid_cache(cache_path, "no_meta.warc.gz")
        assert result is False

    def test_is_valid_cache_wrong_meta(self, downloader):
        """Cache with wrong meta should return False."""
        cache_path = os.path.join(downloader.cache_dir, "wrong_meta.warc.gz")
        with open(cache_path, "w") as f:
            f.write("test")

        meta_path = f"{cache_path}.meta"
        with open(meta_path, "w") as f:
            f.write("different.warc.gz")

        result = downloader._is_valid_cache(cache_path, "test.warc.gz")
        assert result is False
