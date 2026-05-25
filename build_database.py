"""COVID NZ News Database Builder - Main Entry Point.

This script builds a local SQLite database of New Zealand news articles
about COVID-19 from Common Crawl web archive.

Configuration is managed via settings.py - simply import and modify.

Usage:
    uv run build_database.py

To customize:
    1. Edit settings.py or create custom_settings.py
    2. Import your settings: from custom_settings import settings
    3. Run the script

Runtime options (set in settings.py):
    settings.resume = True  # Resume from checkpoint
    settings.use_async = True  # Use async CDX client (10x faster)
"""
import sys
from datetime import datetime

from async_cdx_client import AsyncCDXClient
from cdx_client import CDXClient
from database import NewsDatabase
from logger import setup_logging
from progress import ProgressManager
from settings import settings
from warc_downloader import WARCDownloader
from warc_extractor import WARCExtractor


def extract_publish_date(soup, url: str = '') -> str:
    """
    Extract publish date from HTML metadata with multiple heuristics.

    Args:
        soup: BeautifulSoup parsed HTML
        url: Article URL (for logging/debugging)

    Returns:
        ISO format date string or empty string if not found
    """

    # Try various meta tags for publish date
    date_tags = [
        'article:published_time',
        'og:article:published_time',
        'datePublished',
        'article:date',
        'og:article:published_time',
        'news:publication_date',
        'dc.date',
        'dc.date.created',
        'dc.date.issued',
        'pubdate',
        'publish_date',
    ]

    # Priority order: try property attribute first, then name attribute
    for tag_name in date_tags:
        # Try property attribute (Open Graph, schema.org)
        meta = soup.find('meta', property=tag_name)
        if meta and meta.get('content'):
            content = meta['content']
            parsed = _parse_date(content)
            if parsed:
                return parsed

        # Try name attribute
        meta = soup.find('meta', attrs={'name': tag_name})
        if meta and meta.get('content'):
            content = meta['content']
            parsed = _parse_date(content)
            if parsed:
                return parsed

    # Try time tag with datetime attribute
    time_tag = soup.find('time', attrs={'datetime': True})
    if time_tag:
        datetime_str = time_tag.get('datetime')
        if datetime_str:
            parsed = _parse_date(datetime_str)
            if parsed:
                return parsed

    # Try schema.org structured data
    script_tag = soup.find('script', type='application/ld+json')
    if script_tag:
        try:
            import json
            data = json.loads(script_tag.string)
            if isinstance(data, dict):
                # Try datePublished
                date_pub = data.get('datePublished', '')
                if date_pub:
                    parsed = _parse_date(date_pub)
                    if parsed:
                        return parsed
                # Try dateModified as fallback
                date_mod = data.get('dateModified', '')
                if date_mod:
                    parsed = _parse_date(date_mod)
                    if parsed:
                        return parsed
        except (json.JSONDecodeError, AttributeError):
            pass

    # Try article:modified_time as last resort
    meta = soup.find('meta', property='article:modified_time')
    if meta and meta.get('content'):
        parsed = _parse_date(meta['content'])
        if parsed:
            return parsed

    return ''


def _parse_date(date_str: str) -> str:
    """
    Parse various date formats and return ISO format.

    Args:
        date_str: Date string in various formats

    Returns:
        ISO format date string or empty string if parsing fails
    """
    from datetime import datetime

    if not date_str:
        return ''

    # Common date formats to try
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',      # ISO 8601 with timezone
        '%Y-%m-%dT%H:%M:%SZ',       # ISO 8601 with Z
        '%Y-%m-%dT%H:%M:%S',        # ISO 8601 without timezone
        '%Y-%m-%d %H:%M:%S',        # MySQL datetime
        '%Y-%m-%d',                 # ISO date
        '%d/%m/%Y %H:%M:%S',        # European format
        '%d/%m/%Y',                 # European date
        '%m/%d/%Y %H:%M:%S',        # US format
        '%m/%d/%Y',                 # US date
    ]

    # Normalize the date string
    date_str = date_str.replace('Z', '+00:00').strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

    # Try fromisoformat as fallback (handles many edge cases)
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    return ''


def build_database(logger) -> int:
    """
    Build the news database.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 70)
    logger.info("NZ COVID News Database Builder")
    logger.info("=" * 70)
    logger.info(f"Configuration: {settings}")
    logger.info(f"News sources: {len(settings.news_sources.domains)} domains")
    logger.info(f"Crawl IDs: {len(settings.crawls.crawl_ids)}")
    logger.info(f"Keywords: {len(settings.news_sources.keywords)} terms")
    logger.info(f"Resume mode: {settings.resume}")
    logger.info(f"Async mode: {settings.use_async}")
    logger.info("=" * 70)

    # Initialize progress manager
    progress_manager = ProgressManager(
        checkpoint_file=settings.database.checkpoint_file,
        logger=logger
    )

    # Load or clear checkpoint based on resume flag
    if settings.resume:
        progress_manager.load()
    else:
        progress_manager.clear()

    # Initialize components
    db = NewsDatabase(settings.database.path, logger)

    # Initialize CDX client based on mode
    if settings.use_async:
        cdx_client = AsyncCDXClient(
            rate_limit=settings.network.async_rate_limit,
            max_retries=settings.network.retry_attempts,
            retry_delay=settings.network.retry_delay,
            logger=logger
        )
        logger.info("Using ASYNC CDX client (10x faster)")
    else:
        cdx_client = CDXClient(
            timeout=settings.network.cdx_timeout,
            retry_attempts=settings.network.retry_attempts,
            retry_delay=settings.network.retry_delay,
            logger=logger
        )
        logger.info("Using SYNC CDX client")

    downloader = WARCDownloader(
        cache_dir=settings.cache.directory,
        timeout=settings.network.warc_timeout,
        retry_attempts=settings.network.retry_attempts,
        retry_delay=settings.network.retry_delay,
        logger=logger
    )
    extractor = WARCExtractor(
        min_text_length=settings.extraction.min_text_length,
        max_content_length=settings.extraction.max_content_length,
        allowed_languages=settings.extraction.allowed_languages,
        logger=logger
    )

    # Connect to database
    db.connect()

    # Get remaining work
    remaining_work = progress_manager.get_remaining_work(
        settings.crawls.crawl_ids,
        settings.news_sources.domains
    )

    if not remaining_work:
        logger.info("All work already completed!")
        db.close()
        return 0

    logger.info(f"Remaining work: {len(remaining_work)} crawl-domain pairs")

    total_urls_found = 0
    total_covid_urls = 0
    total_articles = 0
    processed_pairs = 0

    try:
        # Process remaining crawl-domain pairs
        for crawl_id, domain_pattern in remaining_work:
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Processing: {crawl_id} + {domain_pattern}")
            logger.info("=" * 70)

            # Query CDX index
            logger.info("  [1/4] Querying CDX index...")
            urls = cdx_client.query_index(crawl_id, domain_pattern)

            if not urls:
                logger.warning(f"  No URLs found for {domain_pattern}")
                progress_manager.mark_completed(crawl_id, domain_pattern, 0)
                continue

            total_urls_found += len(urls)
            logger.info(f"  Found {len(urls):,} URLs")

            # Filter for COVID keywords
            logger.info("  [2/4] Filtering for COVID-related URLs...")
            covid_urls = cdx_client.filter_keywords(urls, settings.news_sources.keywords)

            if not covid_urls:
                logger.warning(f"  No COVID-related URLs found for {domain_pattern}")
                progress_manager.mark_completed(crawl_id, domain_pattern, 0)
                continue

            total_covid_urls += len(covid_urls)
            logger.info(f"  Found {len(covid_urls):,} COVID-related URLs")

            # Group by WARC file
            warc_files = cdx_client.group_by_warc(covid_urls)
            logger.info(f"  Spanning {len(warc_files)} WARC files")

            # Process WARC files
            logger.info("  [3/4] Processing WARC files...")

            # Limit if configured
            max_files = settings.crawls.max_warc_files_per_crawl
            if max_files:
                warc_files = dict(list(warc_files.items())[:max_files])
                logger.info(f"  Limited to {max_files} WARC files (testing mode)")

            articles_inserted = 0
            from tqdm import tqdm
            for file_idx, (filename, url_entries) in tqdm(enumerate(warc_files.items(), 1), total=len(warc_files), desc="    WARC files", leave=False):
                logger.info(f"    [{file_idx}/{len(warc_files)}] {filename[:50]}...")
                logger.info(f"      Contains {len(url_entries)} COVID-related URLs")

                # Download WARC file
                warc_path = downloader.download(filename)

                if not warc_path:
                    logger.error(f"      Failed to download {filename}")
                    continue

                # Extract articles
                target_urls = {e['url'] for e in url_entries if e.get('url')}
                articles = extractor.extract_from_file(warc_path, target_urls)

                logger.info(f"      Extracted {len(articles)} articles")

                # Save to database with progress bar
                from tqdm import tqdm
                for article in tqdm(articles, desc="  Inserting", leave=False):
                    url_entry = next((e for e in url_entries if e.get('url') == article['url']), {})

                    # Try to extract publish date from HTML
                    publish_date = ''
                    if article.get('html_content'):
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(article['html_content'], 'lxml')
                        publish_date = extract_publish_date(soup, article['url'])

                    if db.insert_article(
                        article['url'],
                        article['title'],
                        article['content'],
                        article['source_domain'],
                        crawl_id,
                        url_entry.get('timestamp', ''),
                        article['language'],
                        article['status_code'],
                        publish_date
                    ):
                        total_articles += 1
                        articles_inserted += 1

            # Save checkpoint after each crawl-domain pair
            progress_manager.mark_completed(crawl_id, domain_pattern, articles_inserted)
            processed_pairs += 1

            logger.info(f"  Completed: {processed_pairs}/{len(remaining_work)} pairs")

        # Summary
        logger.info(f"\n{'=' * 70}")
        logger.info("BUILD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Crawl-domain pairs processed: {processed_pairs}")
        logger.info(f"Total URLs found: {total_urls_found:,}")
        logger.info(f"Covid-related URLs: {total_covid_urls:,}")
        logger.info(f"Articles extracted: {total_articles:,}")
        logger.info(f"Total in database: {db.get_count():,}")

        # Statistics by source
        logger.info("\nArticles by news source:")
        for source, count in db.get_stats_by_source():
            logger.info(f"  {source}: {count:,}")

        # Statistics by language
        logger.info("\nArticles by language:")
        for lang, count in db.get_stats_by_language():
            logger.info(f"  {lang}: {count:,}")

        # Sample recent article
        if db.get_count() > 0:
            logger.info("\nSample recent article:")
            recent = db.get_recent_articles(limit=1)
            if recent:
                article = recent[0]
                logger.info(f"  Title: {article['title']}")
                logger.info(f"  URL: {article['url']}")
                logger.info(f"  Source: {article['source_domain']}")
                logger.info(f"  Content preview: {article['content'][:200]}...")

        logger.info("=" * 70)
        logger.info(f"Database saved to: {settings.database.path}")
        logger.info(f"Build completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\nFatal error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


def main():
    """Main entry point."""
    # Set up logging
    logger = setup_logging(
        log_level=settings.logging.level,
        log_file=settings.logging.file,
        console_output=True
    )

    # Run
    exit_code = build_database(logger)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
