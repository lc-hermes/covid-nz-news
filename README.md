# NZ COVID News Database

A tool to build a local SQLite database of New Zealand news articles about COVID-19 from Common Crawl.

## Overview

This project extracts full-text news articles about COVID-19 from New Zealand news sources (NZ Herald, Stuff, RNZ) using data from the Common Crawl web archive. The extracted articles are stored in a SQLite database for local analysis.

## Features

- Queries Common Crawl CDX index for NZ news URLs containing COVID-related keywords
- Downloads and parses WARC files with caching to avoid re-downloading
- Extracts article title and full text content
- Detects language (filters for English only)
- Stores results in SQLite database with metadata (URL, source domain, crawl ID, timestamp)

## Requirements

- Python 3.10+
- `warcio` - WARC file parsing
- `beautifulsoup4` - HTML parsing
- `lxml` - HTML parser backend
- `langdetect` - Language detection

## Installation

```bash
# Clone the repository
git clone https://github.com/lc-hermes/covid-nz-news.git
cd covid-nz-news

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install warcio beautifulsoup4 lxml langdetect
```

## Usage

Run the main script:

```bash
python build_database.py
```

This will:
1. Query Common Crawl for COVID-related URLs from NZ news domains
2. Download WARC files (cached locally in `warc_cache/`)
3. Extract article content
4. Store results in `covid_nz_news.db`

## Configuration

Edit `build_database.py` to customize:

- `test_crawl`: Common Crawl ID (e.g., "CC-MAIN-2020-16")
- `test_domain`: URL pattern (e.g., "*.nzherald.co.nz/")
- `COVID_KEYWORDS`: List of keywords to filter URLs

## Database Schema

The SQLite database contains an `articles` table with these columns:

- `id` - Primary key
- `url` - Article URL (unique)
- `title` - Article title
- `content` - Full article text (truncated to 50,000 chars)
- `source_domain` - Source domain pattern
- `crawl_id` - Common Crawl ID
- `timestamp` - Crawl timestamp
- `language` - Detected language
- `status_code` - HTTP status code
- `created_at` - When record was inserted

## Querying the Database

```python
import sqlite3

conn = sqlite3.connect('covid_nz_news.db')
cursor = conn.cursor()

# Count articles by source
cursor.execute('SELECT source_domain, COUNT(*) FROM articles GROUP BY source_domain')
print(cursor.fetchall())

# Get recent articles
cursor.execute('SELECT title, content FROM articles ORDER BY timestamp DESC LIMIT 5')
for row in cursor.fetchall():
    print(row[0])
```

## Known Limitations

- Some news sites (e.g., Stuff.co.nz) block Common Crawl bot, resulting in "Denied" pages
- WARC files are large (1-2GB compressed, 5-6GB uncompressed)
- Processing is slow due to WARC decompression
- Some URLs are redirects or landing pages with minimal content

## Performance Tips

- WARC files are cached locally - subsequent runs reuse cached files
- Process fewer WARC files at a time to avoid memory issues
- Use `sqlite3` CLI or a database tool for efficient querying

## License

MIT License

## Acknowledgments

- Data source: [Common Crawl](https://commoncrawl.org/)
- WARC parsing: [warcio](https://github.com/webrecorder/warcio)
