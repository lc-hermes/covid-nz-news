"""Export salience metrics to CSV for analysis.

Command-line tool to calculate and export COVID salience metrics from the database.

Usage:
    uv run export_salience.py [--output-dir ./exports]
"""

import argparse
import os

from database import NewsDatabase
from salience_metrics import SalienceMetrics


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export COVID salience metrics from database")
    parser.add_argument(
        "--db-path",
        type=str,
        default="covid_nz_news.db",
        help="Path to SQLite database (default: covid_nz_news.db)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="exports",
        help="Output directory for CSV files (default: exports)",
    )
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Connect to database
    db = NewsDatabase(args.db_path)
    db.connect()

    # Calculate metrics
    metrics = SalienceMetrics(db)

    # Export articles per day
    daily_df = metrics.get_articles_per_day()
    daily_path = os.path.join(args.output_dir, "articles_per_day.csv")
    daily_df.write_csv(daily_path)
    print(f"Exported daily counts to {daily_path}")

    # Export articles per source
    source_df = metrics.get_articles_per_source()
    source_path = os.path.join(args.output_dir, "articles_per_source.csv")
    source_df.write_csv(source_path)
    print(f"Exported source counts to {source_path}")

    # Export articles per source per day
    daily_source_df = metrics.get_articles_per_source_per_day()
    daily_source_path = os.path.join(args.output_dir, "articles_per_source_per_day.csv")
    daily_source_df.write_csv(daily_source_path)
    print(f"Exported daily source counts to {daily_source_path}")

    # Print summary
    total_articles = len(daily_df)
    print("\nSummary:")
    print(f"  Total articles: {total_articles}")
    print(f"  Date range: {daily_df['date'][0]} to {daily_df['date'][-1]}")
    print(f"  Days with coverage: {len(daily_df)}")
    print(f"  Average articles/day: {total_articles / len(daily_df):.1f}")
    print(f"  Sources: {len(source_df)}")

    db.close()


if __name__ == "__main__":
    main()
