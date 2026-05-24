# NZ COVID News Database

A production-ready tool to build a local SQLite database of New Zealand news articles about COVID-19 from Common Crawl web archive.

## Overview

This project extracts full-text news articles about COVID-19 from New Zealand news sources using data from the Common Crawl web archive. The extracted articles are stored in a SQLite database for local analysis.

## Features

- ✅ Queries Common Crawl CDX index for NZ news URLs containing COVID-related keywords
- ✅ Downloads and parses WARC files with streaming (no memory issues)
- ✅ Caches WARC files locally to avoid re-downloading
- ✅ Extracts article title and full text content with heuristics
- ✅ Detects language (filters for English by default)
- ✅ Stores results in SQLite database with metadata
- ✅ Retry logic with exponential backoff for network failures
- ✅ Configurable via environment variables or command-line arguments
- ✅ Structured logging with file and console output
- ✅ Modular codebase for maintainability

## Quick Start

```bash
# Clone the repository
git clone https://github.com/lc-hermes/covid-nz-news.git
cd covid-nz-news

# Create virtual environment with uv
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Run with defaults
uv run build_database.py

# Or with custom settings
uv run build_database.py --crawl-id CC-MAIN-2020-16 --max-warc-files 5
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Available options:

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAWL_ID` | `CC-MAIN-2020-16` | Common Crawl ID to query |
| `DOMAIN_PATTERN` | `*.nzherald.co.nz/` | URL pattern to search |
| `COVID_KEYWORDS` | `covid,coronavirus,...` | Keywords to filter URLs |
| `MAX_WARC_FILES` | `10` | Max WARC files to process |
| `MAX_CONTENT_LENGTH` | `50000` | Max chars per article |
| `MIN_TEXT_LENGTH` | `100` | Min chars for valid article |
| `RETRY_ATTEMPTS` | `3` | Network retry attempts |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOWED_LANGUAGES` | `en` | Accepted language codes |

### Command-Line Arguments

Override environment variables with CLI flags:

```bash
uv run build_database.py \
  --crawl-id CC-MAIN-2020-32 \
  --domain "*.stuff.co.nz/" \
  --max-warc-files 20 \
  --log-level DEBUG
```

## Project Structure

```
covid-nz-news/
├── build_database.py    # Main entry point
├── config.py           # Configuration management
├── logger.py           # Logging setup
├── cdx_client.py       # Common Crawl CDX client
├── warc_downloader.py  # WARC file downloader with caching
├── warc_extractor.py   # Article extraction from WARC
├── database.py         # SQLite database operations
├── pyproject.toml      # Project dependencies
├── .env.example        # Example environment config
└── README.md           # This file
```

## Database Schema

The SQLite database contains an `articles` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `url` | TEXT | Article URL (unique) |
| `title` | TEXT | Article title |
| `content` | TEXT | Full article text |
| `source_domain` | TEXT | Source domain pattern |
| `crawl_id` | TEXT | Common Crawl ID |
| `timestamp` | TEXT | Crawl timestamp |
| `language` | TEXT | Detected language |
| `status_code` | TEXT | HTTP status code |
| `created_at` | TIMESTAMP | Insert timestamp |

## Querying the Database

```python
import sqlite3

conn = sqlite3.connect('covid_nz_news.db')
cursor = conn.cursor()

# Count articles by source
cursor.execute('SELECT source_domain, COUNT(*) FROM articles GROUP BY source_domain')
print(cursor.fetchall())

# Search by keyword
cursor.execute("SELECT title, url FROM articles WHERE content LIKE ? LIMIT 10", ('%lockdown%',))
for row in cursor.fetchall():
    print(row[0])

# Get recent articles
cursor.execute('SELECT title, timestamp FROM articles ORDER BY timestamp DESC LIMIT 5')
for row in cursor.fetchall():
    print(row)
```

## Development

### Setup for Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run linter
uv run ruff check .

# Run type checker
uv run ty .

# Run tests
uv run pytest
```

### Code Style

This project uses:
- **ruff** for linting and formatting
- **ty** for type checking
- **pytest** for testing

## Known Limitations

- Some news sites (e.g., Stuff.co.nz) block Common Crawl bot, resulting in "Denied" pages
- WARC files are large (1-2GB compressed) - ensure sufficient disk space
- Processing speed depends on network and disk I/O
- Some URLs are redirects or landing pages with minimal content

## Performance Tips

- WARC files are cached locally - subsequent runs reuse cached files
- Adjust `MAX_WARC_FILES` to control processing scope
- Use `--log-level WARNING` to reduce console output
- Query database with `sqlite3` CLI or database tools for efficiency

## Troubleshooting

### Download Failures

If downloads fail repeatedly:
1. Check your network connection
2. Verify the Common Crawl ID exists
3. Increase `RETRY_ATTEMPTS` and `RETRY_DELAY`

### Memory Issues

The extractor uses streaming - you should not encounter memory issues. If you do:
1. Reduce `MAX_WARC_FILES`
2. Check your system memory

### No Articles Found

If no articles are extracted:
1. Verify the domain pattern matches URLs in the crawl
2. Check that keywords appear in URLs (not just content)
3. Try a different `CRAWL_ID`

## License

MIT License

## Acknowledgments

- Data source: [Common Crawl](https://commoncrawl.org/)
- WARC parsing: [warcio](https://github.com/webrecorder/warcio)
- HTML parsing: [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
