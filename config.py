"""Configuration management for COVID NZ News database builder."""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """Configuration settings with environment variable overrides."""

    # Database
    db_path: str = field(default_factory=lambda: os.getenv('DB_PATH', 'covid_nz_news.db'))

    # Cache
    cache_dir: str = field(default_factory=lambda: os.getenv('CACHE_DIR', 'warc_cache'))

    # Common Crawl
    crawl_id: str = field(default_factory=lambda: os.getenv('CRAWL_ID', 'CC-MAIN-2020-16'))
    domain_pattern: str = field(default_factory=lambda: os.getenv('DOMAIN_PATTERN', '*.nzherald.co.nz/'))

    # Keywords
    covid_keywords: List[str] = field(
        default_factory=lambda: os.getenv(
            'COVID_KEYWORDS',
            'covid,coronavirus,virus,lockdown,vaccine,quarantine'
        ).split(',')
    )

    # Processing limits
    max_warc_files: int = field(default_factory=lambda: int(os.getenv('MAX_WARC_FILES', '10')))
    max_content_length: int = field(default_factory=lambda: int(os.getenv('MAX_CONTENT_LENGTH', '50000')))
    min_text_length: int = field(default_factory=lambda: int(os.getenv('MIN_TEXT_LENGTH', '100')))

    # Network
    cdx_timeout: int = field(default_factory=lambda: int(os.getenv('CDX_TIMEOUT', '60')))
    warc_timeout: int = field(default_factory=lambda: int(os.getenv('WARC_TIMEOUT', '300')))
    retry_attempts: int = field(default_factory=lambda: int(os.getenv('RETRY_ATTEMPTS', '3')))
    retry_delay: float = field(default_factory=lambda: float(os.getenv('RETRY_DELAY', '2.0')))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    log_file: str = field(default_factory=lambda: os.getenv('LOG_FILE', 'covid_nz_news.log'))

    # Language filtering
    allowed_languages: List[str] = field(
        default_factory=lambda: os.getenv('ALLOWED_LANGUAGES', 'en').split(',')
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_warc_files < 1:
            raise ValueError("max_warc_files must be at least 1")
        if self.max_content_length < 1000:
            raise ValueError("max_content_length must be at least 1000")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts cannot be negative")
