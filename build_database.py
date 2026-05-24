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
"""
import sys
from datetime import datetime

from cdx_client import CDXClient
from database import NewsDatabase
from logger import setup_logging
from settings import settings
from warc_downloader import WARCDownloader
from warc_extractor import WARCExtractor


def build_database(logger) -> int:
    """
    Build the news database.

    Args:
        logger: Logger instance

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
    logger.info("=" * 70)

    # Initialize components
    db = NewsDatabase(settings.database.path, logger)
    cdx_client = CDXClient(
        timeout=settings.network.cdx_timeout,
        retry_attempts=settings.network.retry_attempts,
        retry_delay=settings.network.retry_delay,
        logger=logger
    )
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

    total_urls_found = 0
    total_covid_urls = 0
    total_articles = 0
    processed_crawls = 0

    try:
        # Process each crawl
        for crawl_idx, crawl_id in enumerate(settings.crawls.crawl_ids, 1):
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Crawl {crawl_idx}/{len(settings.crawls.crawl_ids)}: {crawl_id}")
            logger.info("=" * 70)

            # Process each domain
            for domain_idx, domain_pattern in enumerate(settings.news_sources.domains, 1):
                logger.info(f"\n  [{domain_idx}/{len(settings.news_sources.domains)}] Domain: {domain_pattern}")

                # Query CDX index
                logger.info("    [1/3] Querying CDX index...")
                urls = cdx_client.query_index(crawl_id, domain_pattern)

                if not urls:
                    logger.warning(f"    No URLs found for {domain_pattern}")
                    continue

                total_urls_found += len(urls)
                logger.info(f"    Found {len(urls):,} URLs")

                # Filter for COVID keywords
                logger.info("    [2/3] Filtering for COVID-related URLs...")
                covid_urls = cdx_client.filter_keywords(urls, settings.news_sources.keywords)

                if not covid_urls:
                    logger.warning(f"    No COVID-related URLs found for {domain_pattern}")
                    continue

                total_covid_urls += len(covid_urls)
                logger.info(f"    Found {len(covid_urls):,} COVID-related URLs")

                # Group by WARC file
                warc_files = cdx_client.group_by_warc(covid_urls)
                logger.info(f"    Spanning {len(warc_files)} WARC files")

                # Process WARC files
                logger.info("    [3/3] Processing WARC files...")

                # Limit if configured
                max_files = settings.crawls.max_warc_files_per_crawl
                if max_files:
                    warc_files = dict(list(warc_files.items())[:max_files])
                    logger.info(f"    Limited to {max_files} WARC files (testing mode)")

                for file_idx, (filename, url_entries) in enumerate(warc_files.items(), 1):
                    logger.info(f"      [{file_idx}/{len(warc_files)}] {filename[:50]}...")
                    logger.info(f"        Contains {len(url_entries)} COVID-related URLs")

                    # Download WARC file
                    warc_path = downloader.download(filename)

                    if not warc_path:
                        logger.error(f"        Failed to download {filename}")
                        continue

                    # Extract articles
                    target_urls = {e['url'] for e in url_entries if e.get('url')}
                    articles = extractor.extract_from_file(warc_path, target_urls)

                    logger.info(f"        Extracted {len(articles)} articles")

                    # Save to database
                    for article in articles:
                        url_entry = next((e for e in url_entries if e.get('url') == article['url']), {})

                        if db.insert_article(
                            article['url'],
                            article['title'],
                            article['content'],
                            article['source_domain'],
                            crawl_id,
                            url_entry.get('timestamp', ''),
                            article['language'],
                            article['status_code']
                        ):
                            total_articles += 1

            processed_crawls += 1

        # Summary
        logger.info(f"\n{'=' * 70}")
        logger.info("BUILD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Crawls processed: {processed_crawls}/{len(settings.crawls.crawl_ids)}")
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
