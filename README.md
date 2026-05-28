# NZ COVID News Database

A production-ready tool to build a local Delta Lake database of New Zealand news articles about COVID-19 from Common Crawl web archive. Designed for creating comprehensive COVID salience timelines.

## Overview

This project extracts full-text articles from major NZ news sources during the COVID-19 pandemic (2020-2022) and stores them in a Delta Lake table for analysis.

### Key Features

- **Multi-source**: Captures articles from 6 major NZ news outlets
- **Multi-crawl**: Processes 24 Common Crawl snapshots from 2020-2022
- **Memory-efficient**: Streaming WARC parsing (handles 5-6GB files)
- **Production-ready**: Full type checking, linting, CI/CD with coverage
- **Easy configuration**: Single Python config file (no CLI args)
- **Content deduplication**: MD5 hash-based deduplication with normalization
- **Publish date extraction**: Extracts actual publish dates from HTML metadata
- **Delta Lake storage**: ACID transactions, time travel, schema evolution
- **Polars backend**: Fast DataFrame operations with lazy evaluation
- **Partitioned storage**: Efficient filtering by source domain
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

The Delta Lake table uses the following schema:

```
┌─────────────────┬───────┐
│ url             │ Utf8  │
│ title           │ Utf8  │
│ content         │ Utf8  │
│ content_hash    │ Utf8  │
│ source_domain   │ Utf8  │
│ crawl_id        │ Utf8  │
│ timestamp       │ Utf8  │
│ language        │ Utf8  │
│ status_code     │ Utf8  │
│ publish_date    │ Utf8  │
└─────────────────┴───────┘
```

### Partitioning

The table is partitioned by `source_domain` for efficient filtering by news source.

### Delta Lake Features

- **ACID transactions**: Safe concurrent writes
- **Time travel**: Query historical versions with `dt.version()`
- **Schema evolution**: Add columns without migration
- **Optimization**: `dt.optimize.compact()` to merge small files
- **Vacuum**: `dt.vacuum(retention_hours)` to remove old files

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
from delta_database import DeltaNewsDatabase

db = DeltaNewsDatabase("covid_nz_news_delta")
db.init_table()

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

# Get articles by date range
articles = db.get_articles_by_date_range(
    start_date="2020-03-01",
    end_date="2020-04-30",
    limit=1000
)

# Query all articles with specific columns
all_articles = db.query_all_articles(
    columns=["url", "title", "source_domain", "publish_date"]
)

# Get Delta table version (for time travel)
print(f"Current version: {db.version()}")

# Get table history
history = db.history(limit=10)
```

## Export to HuggingFace

Export the database as a HuggingFace dataset for sharing and publishing:

```bash
# Install HuggingFace dependencies
uv pip install -e ".[huggingface]"

# Export locally
uv run export_huggingface.py

# Push to HuggingFace Hub
HF_TOKEN=your_token uv run export_huggingface.py --push --repo-name your-username/covid-nz-news
```

This creates a dataset in the standard HuggingFace format that can be:
- Loaded directly with `datasets.load_dataset()`
- Published to the HuggingFace Hub
- Used with any ML framework (PyTorch, TensorFlow, etc.)

### Using the exported dataset

```python
from datasets import load_dataset

# Load from local path
dataset = load_dataset("covid_nz_news_dataset", data_dir="covid_nz_news_dataset")

# Or load from HuggingFace Hub
dataset = load_dataset("lc-hermes/covid-nz-news")

# Access data
print(f"Total articles: {len(dataset['train'])}")
print(dataset['train'][0])  # First article
```

## LLM Classification

Classify articles into categories using a local LLM server (OpenAI-compatible API):

```bash
# Install LLM dependencies
uv pip install -e ".[llm]"

# Classify first 100 articles
uv run llm_pipeline.py --limit 100

# Classify all articles with resume support
uv run llm_pipeline.py --resume

# Use a different LLM server
uv run llm_pipeline.py --llm-url http://localhost:8000 --model llama-2-7b
```

### Default Categories

The pipeline classifies articles into these categories:
- `health_outcomes` - Cases, deaths, hospitalizations, ICU
- `vaccination` - Vaccine rollout, efficacy, mandates
- `lockdown_measures` - Restrictions, alert levels, curfews
- `border_policy` - Quarantine, managed isolation, travel
- `economic_impact` - Business closures, job losses, support
- `public_behavior` - Mask mandates, social distancing
- `government_response` - Policy announcements, cabinet decisions
- `science_research` - Variants, studies, scientific findings
- `international` - Global context, other countries
- `miscellaneous` - Other COVID-related content

### Using the Classifications

```python
import polars as pl

# Load classifications
df = pl.read_parquet("llm_classifications.parquet")

# Filter by category
vaccine_articles = df.filter(pl.col("category") == "vaccination")

# Count by category
counts = df.group_by("category").agg(pl.col("url").count())
print(counts)

# Join with original data for full article access
original = pl.scan_delta("covid_nz_news_delta").collect()
merged = original.join(df, on="url", how="left")
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

Use the built-in salience metrics module with Delta Lake:

```python
from delta_database import DeltaNewsDatabase
from salience_metrics import SalienceMetrics

db = DeltaNewsDatabase("covid_nz_news_delta")
db.init_table()

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
```

Or use Polars directly for custom analysis:

```python
from delta_database import DeltaNewsDatabase

db = DeltaNewsDatabase("covid_nz_news_delta")
db.init_table()

# Get the Polars DataFrame
df = db.table.to_polars()

# Articles per day
daily = df.group_by("timestamp").agg(
    pl.col("url").count().alias("count")
).sort("timestamp")

print(daily)

# Articles per source
by_source = df.group_by("source_domain").agg(
    pl.col("url").count().alias("count")
).sort("count", descending=True)

print(by_source)

# Filter by date range
filtered = df.filter(
    (pl.col("publish_date") >= "2020-03-01") &
    (pl.col("publish_date") <= "2020-04-30")
)

print(f"Articles in date range: {filtered.height}")
```

## Project Structure

```
covid-nz-news/
├── build_database.py       # Main entry point
├── export_huggingface.py   # Export to HuggingFace dataset format
├── generate_trend_plot.py  # Generate trend visualization
├── llm_pipeline.py         # LLM classification pipeline
├── llm_config.py           # LLM configuration
├── llm_client.py           # LLM client for OpenAI-compatible servers
├── settings.py             # Configuration (importable)
├── cdx_client.py           # Common Crawl CDX client
├── delta_database.py       # Delta Lake + Polars operations
├── logger.py               # Logging setup
├── warc_downloader.py      # WARC file downloader
├── warc_extractor.py       # WARC file parser
├── .env.example            # Environment variable template
├── pyproject.toml          # Dependencies
├── README.md               # This file
└── .github/
    └── workflows/
        └── ci.yml          # CI pipeline
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
3. **Delta Lake storage**: Requires more disk space than SQLite for small datasets (overhead of partitioned storage)

## Future Improvements

- [x] Export to HuggingFace dataset format (see `export_huggingface.py`)
- [x] LLM classification pipeline (see `llm_pipeline.py`)
- [ ] Export to CSV/JSON using Polars (`df.write_csv()`, `df.write_json()`)
- [ ] Advanced salience metrics (topic modeling, sentiment analysis)
- [ ] Interactive Jupyter notebook for exploration
- [ ] API endpoint for querying database
- [ ] Delta Lake time travel examples (query historical versions)
- [ ] Schema evolution examples (add columns without migration)

## License

MIT

## Author

Built for COVID-19 salience analysis in New Zealand news media.
