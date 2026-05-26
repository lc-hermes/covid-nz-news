#!/usr/bin/env python3
"""Export all articles from the covid-nz-news database to CSV/JSON.

The script loads the database via the existing NewsDatabase class and
writes two files:

* articles.csv ─ CSV with row fields: url, title, content, source_domain,
  language, status_code, timestamp
* articles.json ─ JSON array of all article objects

The script uses the default database path from settings.py.
"""

import json
import csv
from pathlib import Path

from settings import settings
from database import NewsDatabase

DB_PATH = Path(settings.database.path)

OUTPUT_DIR = Path("./export_output")
OUTPUT_DIR.mkdir(exist_ok=True)

CSV_PATH = OUTPUT_DIR / "articles.csv"
JSON_PATH = OUTPUT_DIR / "articles.json"

if __name__ == "__main__":
    with NewsDatabase(str(DB_PATH)) as db:
        articles = db.query_all_articles()
        if not articles:
            print("No articles found in database.")
            exit(0)

        # Write CSV
        with CSV_PATH.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "url",
                "title",
                "content",
                "source_domain",
                "language",
                "status_code",
                "timestamp",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for a in articles:
                writer.writerow({k: a.get(k, "") for k in fieldnames})

        # Write JSON
        with JSON_PATH.open("w", encoding="utf-8") as jsfile:
            json.dump(articles, jsfile, ensure_ascii=False, indent=2)

        print(f"Exported {len(articles)} articles to {CSV_PATH} and {JSON_PATH}")
