"""
Configuration for COVID NZ News Database Builder.

This file can be imported directly:
    from config import settings

Or modified to customize the data collection:
    settings.NZ_NEWS_DOMAINS = ['*.stuff.co.nz/', '*.nzherald.co.nz/']
    settings.CRAWL_IDS = ['CC-MAIN-2020-16', 'CC-MAIN-2020-32']
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DatabaseConfig:
    """Database configuration."""

    path: str = "covid_nz_news_delta"
    checkpoint_file: str = "build_progress.json"


@dataclass
class CacheConfig:
    """Cache configuration."""

    directory: str = "warc_cache"


@dataclass
class NetworkConfig:
    """Network configuration."""

    cdx_timeout: int = 60
    warc_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: float = 2.0
    async_rate_limit: int = 10  # requests per second for async mode


@dataclass
class ExtractionConfig:
    """Article extraction configuration."""

    max_content_length: int = 50000
    min_text_length: int = 100
    allowed_languages: List[str] = field(default_factory=lambda: ["en"])


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file: str = "covid_nz_news.log"


@dataclass
class NewsSourceConfig:
    """News source configuration."""

    # Major NZ news domains - add more for comprehensive coverage
    domains: List[str] = field(
        default_factory=lambda: [
            "*.stuff.co.nz/",  # Stuff - largest NZ news site
            "*.nzherald.co.nz/",  # NZ Herald
            "*.rnz.co.nz/",  # Radio New Zealand (public broadcaster)
            "*.newsroom.co.nz/",  # Newsroom
            "*.tvnz.co.nz/",  # TVNZ
            "*.3news.co.nz/",  # 3News
            "*.one-news.co.nz/",  # One News
            "*.biznews.co.nz/",  # BizzNews
        ]
    )

    # COVID-related keywords for filtering (URL + content)
    keywords: List[str] = field(
        default_factory=lambda: [
            # Core disease terms
            "covid",
            "coronavirus",
            "sars-cov-2",
            "virus",
            # Pandemic terminology
            "pandemic",
            "outbreak",
            "epidemic",
            "infection",
            "infections",
            "transmission",
            "contagion",
            # Healthcare response
            "vaccine",
            "vaccination",
            "vaccines",
            "immunisation",
            "hospital",
            "hospitalised",
            "icu",
            "ventilator",
            "health",
            "ministry of health",
            "director-general",
            "medical",
            # Government measures
            "lockdown",
            "alert level",
            "state of emergency",
            "quarantine",
            "isolation",
            "border",
            "travel ban",
            "border closure",
            "biosecurity",
            # Public health measures
            "social distancing",
            "physical distancing",
            "face mask",
            "mask",
            "hand sanitiser",
            "hygiene",
            "covid tracer",
            "contact tracing",
            "trace",
            # Restrictions and reopening
            "restric",  # catches restriction, restrictions, restricted
            "reopening",
            "curfew",
            "gathering limit",
            "stay home",
            "stay home order",
            # Statistics
            "cases",
            "deaths",
            "fatalities",
            "positives",
            "rt rate",
            "reproduction rate",
            # Variants
            "variant",
            "omicron",
            "delta",
            "alpha",
            "beta",
            "gamma",
            # Economic impact
            "jobkeeper",
            "support",
            "business",
            "economic",
        ]
    )


@dataclass
class CrawlConfig:
    """Common Crawl configuration."""

    # COVID timeline: March 2020 - December 2022
    # NOTE: Only these 3 crawl IDs contained NZ news data (15 others returned 0 URLs)
    # Each crawl is biweekly, format: CC-MAIN-YYYY-N (N = 1-26)
    crawl_ids: List[str] = field(
        default_factory=lambda: [
            "CC-MAIN-2020-16",  # April 2020 - 550 articles
            "CC-MAIN-2020-24",  # June 2020 - 423 articles
            "CC-MAIN-2020-40",  # October 2020 - 14 articles
            # NOTE: These crawls had NO NZ news data (removed for efficiency):
            # CC-MAIN-2020-48, CC-MAIN-2021-8 through CC-MAIN-2022-48
        ]
    )

    # Optional date range filter (ISO format dates)
    # If set, only URLs within this date range will be extracted
    # Example: date_start="2020-04-01", date_end="2020-06-30"
    date_start: Optional[str] = None
    date_end: Optional[str] = None

    # Limit for testing - set to None for full run
    max_warc_files_per_crawl: int | None = None


class Settings:
    """Main settings container."""

    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    network: NetworkConfig = NetworkConfig()
    extraction: ExtractionConfig = ExtractionConfig()
    logging: LoggingConfig = LoggingConfig()
    news_sources: NewsSourceConfig = NewsSourceConfig()
    crawls: CrawlConfig = CrawlConfig()

    # Runtime configuration (set via settings.py, not CLI)
    resume: bool = True  # Resume from checkpoint
    use_async: bool = False  # Use async CDX client (experimental)

    def __repr__(self) -> str:
        return (
            f"Settings(\n"
            f"  domains={len(self.news_sources.domains)} sources,\n"
            f"  crawls={len(self.crawls.crawl_ids)} crawl IDs,\n"
            f"  keywords={len(self.news_sources.keywords)} keywords\n"
            f")"
        )


# Default settings instance
settings = Settings()
