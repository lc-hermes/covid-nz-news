"""COVID NZ News Database Builder - Main Entry Point.

This script builds a local SQLite database of New Zealand news articles
about COVID-19 from Common Crawl web archive.

Usage:
    uv run build_database.py
    uv run build_database.py --crawl-id CC-MAIN-2020-16 --domain "*.nzherald.co.nz/"
    uv run build_database.py --max-warc-files 5 --log-level DEBUG

Environment Variables:
    See .env.example for available configuration options.
"""
import argparse
import sys

from cdx_client import CDXClient
from config import Config
from database import NewsDatabase
from logger import setup_logging
from warc_downloader import WARCDownloader
from warc_extractor import WARCExtractor


def build_database(args, config: Config, logger) -> int:
    """
    Build the news database.

    Args:
        args: Command line arguments
        config: Configuration object
        logger: Logger instance

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info("NZ COVID News Database Builder")
    logger.info("=" * 60)
    logger.info(f"Crawl ID: {config.crawl_id}")
    logger.info(f"Domain: {config.domain_pattern}")
    logger.info(f"Max WARC files: {config.max_warc_files}")
    logger.info(f"Keywords: {', '.join(config.covid_keywords)}")
    logger.info(f"Allowed languages: {', '.join(config.allowed_languages)}")
    logger.info("=" * 60)

    # Initialize components
    db = NewsDatabase(config.db_path, logger)
    cdx_client = CDXClient(
        timeout=config.cdx_timeout,
        retry_attempts=config.retry_attempts,
        retry_delay=config.retry_delay,
        logger=logger
    )
    downloader = WARCDownloader(
        cache_dir=config.cache_dir,
        timeout=config.warc_timeout,
        retry_attempts=config.retry_attempts,
        retry_delay=config.retry_delay,
        logger=logger
    )
    extractor = WARCExtractor(
        min_text_length=config.min_text_length,
        max_content_length=config.max_content_length,
        allowed_languages=config.allowed_languages,
        logger=logger
    )

    # Connect to database
    db.connect()

    try:
        # Query CDX index
        logger.info("\n[1/4] Querying CDX index...")
        urls = cdx_client.query_index(config.crawl_id, config.domain_pattern)

        if not urls:
            logger.error("No URLs found in CDX index!")
            return 1

        # Filter for COVID keywords
        logger.info("\n[2/4] Filtering for COVID-related URLs...")
        covid_urls = cdx_client.filter_keywords(urls, config.covid_keywords)

        if not covid_urls:
            logger.error("No COVID-related URLs found!")
            return 1

        # Group by WARC file
        warc_files = cdx_client.group_by_warc(covid_urls)

        # Process WARC files
        logger.info("\n[3/4] Processing WARC files...")
        processed = 0
        skipped = 0
        failed_urls = 0

        for i, (filename, url_entries) in enumerate(list(warc_files.items())[:config.max_warc_files]):
            logger.info(f"\n  [{i+1}/{min(config.max_warc_files, len(warc_files))}] {filename[:50]}...")
            logger.info(f"    Contains {len(url_entries)} COVID-related URLs")

            # Download WARC file
            warc_path = downloader.download(filename)

            if not warc_path:
                logger.error(f"    Failed to download {filename}")
                failed_urls += len(url_entries)
                continue

            # Extract articles
            target_urls = {e['url'] for e in url_entries if e.get('url')}
            articles = extractor.extract_from_file(warc_path, target_urls)

            logger.info(f"    Extracted {len(articles)} articles")

            # Save to database
            for article in articles:
                url_entry = next((e for e in url_entries if e.get('url') == article['url']), {})

                if db.insert_article(
                    article['url'],
                    article['title'],
                    article['content'],
                    article['source_domain'],
                    config.crawl_id,
                    url_entry.get('timestamp', ''),
                    article['language'],
                    article['status_code']
                ):
                    processed += 1
                else:
                    failed_urls += 1

            skipped += len(url_entries) - len(articles)

        # Summary
        logger.info("\n[4/4] Summary")
        logger.info("=" * 60)
        logger.info(f"Total URLs found: {len(urls):,}")
        logger.info(f"COVID-related URLs: {len(covid_urls):,}")
        logger.info(f"WARC files processed: {min(config.max_warc_files, len(warc_files))}")
        logger.info(f"Articles extracted: {processed:,}")
        logger.info(f"Articles skipped: {skipped:,}")
        logger.info(f"Failed URLs: {failed_urls:,}")
        logger.info(f"Total in database: {db.get_count():,}")

        # Statistics
        logger.info("\nArticles by source:")
        for source, count in db.get_stats_by_source():
            logger.info(f"  {source}: {count:,}")

        logger.info("\nArticles by language:")
        for lang, count in db.get_stats_by_language():
            logger.info(f"  {lang}: {count:,}")

        # Sample
        if db.get_count() > 0:
            logger.info("\nSample recent article:")
            recent = db.get_recent_articles(limit=1)
            if recent:
                article = recent[0]
                logger.info(f"  Title: {article['title']}")
                logger.info(f"  URL: {article['url']}")
                logger.info(f"  Content preview: {article['content'][:200]}...")

        logger.info("=" * 60)
        logger.info("Database build complete!")
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
    parser = argparse.ArgumentParser(
        description='Build a local SQLite database of NZ news articles about COVID-19 from Common Crawl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run build_database.py
  uv run build_database.py --crawl-id CC-MAIN-2020-16
  uv run build_database.py --max-warc-files 5 --log-level DEBUG

Environment:
  Copy .env.example to .env and configure settings there.
  Command line arguments override environment variables.
        """
    )
    parser.add_argument(
        '--crawl-id',
        help='Common Crawl ID (e.g., CC-MAIN-2020-16)'
    )
    parser.add_argument(
        '--domain',
        help='Domain pattern (e.g., *.nzherald.co.nz/)'
    )
    parser.add_argument(
        '--max-warc-files',
        type=int,
        help='Maximum number of WARC files to process'
    )
    parser.add_argument(
        '--db-path',
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--cache-dir',
        help='Directory for caching WARC files'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Logging level'
    )
    parser.add_argument(
        '--keywords',
        help='Comma-separated COVID keywords'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config()

        # Override with command line args
        if args.crawl_id:
            config.crawl_id = args.crawl_id
        if args.domain:
            config.domain_pattern = args.domain
        if args.max_warc_files:
            config.max_warc_files = args.max_warc_files
        if args.db_path:
            config.db_path = args.db_path
        if args.cache_dir:
            config.cache_dir = args.cache_dir
        if args.keywords:
            config.covid_keywords = args.keywords.split(',')

        # Set log level from args or config
        log_level = args.log_level or config.log_level

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Set up logging
    logger = setup_logging(
        log_level=log_level,
        log_file=config.log_file,
        console_output=True
    )

    # Run
    exit_code = build_database(args, config, logger)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
