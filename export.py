"""Export COVID NZ News metrics.

This module provides a CLI entry point ``python -m export`` that reads the
``covid_nz_news`` SQLite database and writes three CSV files:

* ``articles_per_day.csv`` – counts of articles per day
* ``articles_per_source.csv`` – counts per source domain
* ``articles_per_source_per_day.csv`` – counts per source per day

A JSON representation of each table is also written if the ``--output‑format``
is set to ``json`` (the default is ``csv``).  The JSON files contain a
list of row dictionaries.

The functions are deliberately lightweight and only depend on the existing
``database`` and ``salience_metrics`` modules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from database import NewsDatabase
from salience_metrics import SalienceMetrics

__all__ = ["export_to_csv_json", "main"]


def export_to_csv_json(db_path: str | Path, out_dir: str | Path, fmt: str = "csv") -> int:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    db = NewsDatabase(str(db_path))
    db.connect()
    metrics = SalienceMetrics(db)

    daily = metrics.get_articles_per_day()
    source = metrics.get_articles_per_source()
    daily_source = metrics.get_articles_per_source_per_day()

    total_rows = 0

    def _write(df, prefix: str, fmt: str) -> None:
        nonlocal total_rows
        out_path = out_dir / f"{prefix}.{ 'csv' if fmt == 'csv' else 'json'}"
        if fmt == "csv":
            df.write_csv(out_path)
        else:
            rows = df.to_dicts()
            with open(out_path, "w", encoding="utf-8") as fp:
                json.dump(rows, fp, indent=2, ensure_ascii=False)
        total_rows += len(df)

    _write(daily, "articles_per_day", fmt)
    _write(source, "articles_per_source", fmt)
    _write(daily_source, "articles_per_source_per_day", fmt)

    db.close()
    return total_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export COVID NZ News metrics")
    parser.add_argument("--db-path", default="covid_nz_news.db", help="SQLite database path")
    parser.add_argument("--output-dir", default="exports", help="Output directory")
    parser.add_argument(
        "--output-format", choices=["csv", "json"], default="csv", help="File format"
    )
    args = parser.parse_args()

    export_to_csv_json(args.db_path, args.output_dir, args.output_format)


if __name__ == "__main__":
    main()
