#!/usr/bin/env python3
"""Placeholder exporter that writes dummy CSV/JSON files.
"""

import argparse
import csv
import json
from pathlib import Path

__all__ = ["export_to_csv_json", "main"]

def export_to_csv_json(db_path: str | Path, out_dir: str | Path, fmt: str = "csv") -> int:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Dummy data
    rows = [
        {"date": "2023-01-01", "count": 5},
        {"date": "2023-01-02", "count": 3},
    ]
    out_path = out_dir / f"dummy.{fmt if fmt in ("csv", "json") else "csv"}"
    if fmt == "csv":
        with out_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    else:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export placeholder data")
    parser.add_argument("--db-path", default="covid_nz_news.db", help="SQLite database path")
    parser.add_argument("--output-dir", default="exports", help="Output directory")
    parser.add_argument("--output-format", choices=["csv", "json"], default="csv", help="File format")
    args = parser.parse_args()
    export_to_csv_json(args.db_path, args.output_dir, args.output_format)

if __name__ == "__main__":
    main()
