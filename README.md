# NZ COVID News Database

A production-ready tool to build a local SQLite database of New Zealand news articles about COVID-19 from Common Crawl web archive. Designed for creating comprehensive COVID salience timelines.

## Overview

This project extracts full-text articles from major NZ news sources during the COVID-19 pandemic (2020-2022) and stores them in a SQLite database for analysis.

### Key Features

- **Multi-source**: Captures articles from 6 major NZ news outlets
- **Multi-crawl**: Processes 24 Common Crawl snapshots from 2020-2022
- **Memory-efficient**: Streaming WARC parsing (handles 5-6GB files)
- **Production-ready**: Full type checking, linting, CI/CD
- **Easy configuration**: Single Python config file (no CLI args)

## News Sources

The default configuration includes these major NZ news sources:

1. **Stuff** (`*.stuff.co.nz/`) - Largest NZ news site
2. **NZ Herald** (`*.nzherald.co.nz/`) - Major national newspaper
3. **RNZ** (`*.rnz.co.nz/`) - Public broadcaster
4. **TVNZ** (`*.tvnz.co.nz/`) - TVNZ news
5. **3News** (`*.3news.co.nz/`) - 3News
6. **Newsroom** (`*.newsroom.co.nz/`) - Newsroom

## COVID Keywords

Articles are filtered using these COVID-related terms:

- **Core terms**: covid, coronavirus, virus
- **Policy**: lockdown, vaccine, quarantine, border, travel bubble
- **Variants**: omicron, delta, alpha, beta, gamma
- **Health metrics**: cases, deaths, hospitalization, ICU
- **NZ-specific**: managed isolation, alert level, restrictions, curfew, mask mandate

## Quick Start

### 1. Set up environment

```bash
cd covid-nz-news
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. Configure (optional)

Edit `settings.py` to customize:

```python
from settings import settings

# Change database path
settings.database.path = "my_covid_db.db"

# Add more news sources
settings.news_sources.domains.append("*.yourdomain.co.nz/")

# Limit for testing
settings.crawls.max_warc_files_per_crawl = 1  # Set to None for full run
```

### 3. Run

```bash
uv run build_database.py
```

## Configuration

All configuration is in `settings.py` - simply import and modify:

```python
from settings import settings

# Database
settings.database.path = "covid_nz_news.db"

# Cache
settings.cache.directory = "warc_cache"

# News sources
settings.news_sources.domains = [
    "*.stuff.co.nz/",
    "*.nzherald.co.nz/",
    "*.rnz.co.nz/",
]

# COVID keywords
settings.news_sources.keywords = [
    "covid", "coronavirus", "lockdown", "vaccine"
]

# Crawls to process
settings.crawls.crawl_ids = [
    "CC-MAIN-2020-16",
    "CC-MAIN-2020-24",
]

# Limits
settings.crawls.max_warc_files_per_crawl = 10  # None = no limit
```

### Configuration Sections

- **database**: SQLite database path
- **cache**: WARC file cache directory
- **network**: Timeouts and retry settings
- **extraction**: Content length limits, language filtering
- **logging**: Log level and file
- **news_sources**: Domain patterns and keywords
- **crawls**: List of Common Crawl IDs to process

## Database Schema

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT,
    source_domain TEXT,
    crawl_id TEXT,
    timestamp TEXT,
    language TEXT,
    status_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

- `idx_url` - Fast URL lookup
- `idx_source` - Group by news source
- `idx_timestamp` - Timeline analysis
- `idx_language` - Language filtering

## Querying the Database

```python
from database import NewsDatabase

db = NewsDatabase("covid_nz_news.db")
db.connect()

# Get article count
print(f"Total articles: {db.get_count()}")

# Get stats by source
for source, count in db.get_stats_by_source():
    print(f"{source}: {count} articles")

# Search by keyword
articles = db.search_by_keyword("vaccine", limit=10)
for article in articles:
    print(f"{article['title']}: {article['url']}")

# Get recent articles
recent = db.get_recent_articles(limit=10)

# Custom query
articles = db.query_articles(
    where="source_domain = ?",
    params=("stuff.co.nz",),
    limit=50
)

db.close()
```

## Analysis Example: COVID Salience Timeline

```python
import sqlite3
from collections import defaultdict
from datetime import datetime

conn = sqlite3.connect("covid_nz_news.db")
cursor = conn.cursor()

# Articles per day
cursor.execute("""
    SELECT timestamp, COUNT(*) as count
    FROM articles
    WHERE timestamp IS NOT NULL
    GROUP BY timestamp
    ORDER BY timestamp
""")

daily_counts = defaultdict(int)
for timestamp, count in cursor.fetchall():
    daily_counts[timestamp] = count

# Print timeline
for date in sorted(daily_counts.keys()):
    print(f"{date}: {daily_counts[date]} articles")

conn.close()
```

## Project Structure

```
covid-nz-news/
├── build_database.py    # Main entry point
├── settings.py          # Configuration (importable)
├── config.py            # Legacy (deprecated)
├── cdx_client.py        # Common Crawl CDX client
├── database.py          # SQLite operations
├── logger.py            # Logging setup
├── warc_downloader.py   # WARC file downloader
├── warc_extractor.py    # WARC file parser
├── .env.example         # Environment variable template
├── pyproject.toml       # Dependencies
├── README.md            # This file
└── .github/
    └── workflows/
        └── ci.yml       # CI pipeline
```

## Quality Assurance

- **Type checking**: `ty` (all checks pass)
- **Linting**: `ruff` (all checks pass)
- **CI/CD**: GitHub Actions on every push

Run checks locally:

```bash
uv run ruff check .
uv run ty check .
```

## Common Crawl Coverage

The default configuration processes 24 Common Crawl snapshots:

- **2020**: 6 crawls (April - December) - Initial outbreak
- **2021**: 6 crawls (February - December) - Vaccination rollout
- **2022**: 6 crawls (February - December) - Omicron and easing

Total coverage: ~2 years of NZ COVID news coverage.

## Limitations

1. **Publish date vs crawl date**: Currently uses WARC timestamp (crawl time), not article publish date
2. **No deduplication**: Same article may appear multiple times if URL differs
3. **No export**: Data is in SQLite only (no CSV/JSON export yet)
4. **No progress tracking**: No checkpoint/resume functionality

## Future Improvements

- [ ] Extract publish date from article HTML
- [ ] Content-based deduplication
- [ ] Export to CSV/JSON
- [ ] Progress checkpointing
- [ ] Salience metrics calculation
- [ ] Timeline visualization

## License

MIT

## Author

Built for COVID-19 salience analysis in New Zealand news media.
