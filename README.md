# NZ COVID News Database

A production-ready tool to build a local SQLite database of New Zealand news articles about COVID-19 from Common Crawl web archive. Designed for creating comprehensive COVID salience timelines.

## Overview

This project extracts full-text articles from major NZ news sources during the COVID-19 pandemic (2020-2022) and stores them in a SQLite database for analysis.

### Key Features

- **Multi-source**: Captures articles from 6 major NZ news outlets
- **Multi-crawl**: Processes 24 Common Crawl snapshots from 2020-2022
- **Memory-efficient**: Streaming WARC parsing (handles 5-6GB files)
- **Production-ready**: Full type checking, linting, CI/CD with coverage
- **Easy configuration**: Single Python config file (no CLI args)
- **Content deduplication**: MD5 hash-based deduplication with normalization
- **Publish date extraction**: Extracts actual publish dates from HTML metadata
- **Visualization tools**: Built-in plotting for salience timeline analysis
- **Progress tracking**: TQDM progress bars for long-running builds

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

# Runtime options
settings.resume = False  # Resume from checkpoint (skip already processed)
settings.use_async = False  # Use async CDX client (10x faster)

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
    content_hash TEXT,
    source_domain TEXT,
    crawl_id TEXT,
    timestamp TEXT,
    language TEXT,
    status_code TEXT,
    publish_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

- `idx_url` - Fast URL lookup
- `idx_source` - Group by news source
- `idx_timestamp` - Timeline analysis
- `idx_language` - Language filtering
- `idx_publish_date` - Sort by actual publish date
- `idx_content_hash` - Deduplication lookup

## Visualization

Generate plots of the COVID salience timeline:

```bash
uv run visualize_salience.py --db-path covid_nz_news.db --output-dir ./exports
```

This generates three visualization files:
- `covid_salience_timeline.png` - Daily article counts with 7-day rolling average
- `articles_by_source.png` - Bar chart of articles per news source
- `stacked_timeline_by_source.png` - Stacked area chart showing coverage over time

### Installation

Visualization requires matplotlib:

```bash
uv pip install matplotlib
```

Or install with the viz extras:

```bash
uv pip install -e ".[viz]"
```

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

## Visualization

Generate plots of the COVID salience timeline:

```bash
uv run visualize_salience.py --db-path covid_nz_news.db --output-dir ./exports
```

This generates:
- `covid_salience_timeline.png` - Daily article counts with 7-day rolling average
- `articles_by_source.png` - Bar chart of articles per news source
- `stacked_timeline_by_source.png` - Stacked area chart showing coverage over time

Install visualization dependencies:
```bash
uv pip install matplotlib
```

## Analysis Tools

Use the built-in salience metrics module:

```python
from database import NewsDatabase
from salience_metrics import SalienceMetrics

db = NewsDatabase("covid_nz_news.db")
db.connect()

metrics = SalienceMetrics(db)

# Get articles per day
daily = metrics.get_articles_per_day()
print(daily)

# Get articles per source
by_source = metrics.get_articles_per_source()
print(by_source)

# Get total statistics
stats = metrics.get_total_statistics()
print(f"Total articles: {stats['total_articles']}")
print(f"Date range: {stats['date_earliest']} to {stats['date_latest']}")

db.close()
```

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

1. **Publish date extraction**: Not all articles have publish dates in HTML metadata; falls back to crawl date
2. **Deduplication sensitivity**: MD5 hash-based deduplication may miss near-duplicates with minor content changes
3. **No export**: Data is in SQLite only (no CSV/JSON export yet)

## Future Improvements

- [ ] Export to CSV/JSON
- [ ] Advanced salience metrics (topic modeling, sentiment analysis)
- [ ] Interactive Jupyter notebook for exploration
- [ ] API endpoint for querying database

## License

MIT

## Author

Built for COVID-19 salience analysis in New Zealand news media.
