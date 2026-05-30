"""Analyze COVID NZ News data in Delta Lake.

Shows what we have, what's missing, and progress tracking.
"""

import json
from datetime import datetime
from pathlib import Path

import polars as pl

from settings import settings


def analyze_delta_lake():
    """Analyze data stored in Delta Lake."""
    delta_path = Path(settings.database.path)

    if not delta_path.exists():
        print("No Delta Lake data found!")
        return

    print("=" * 70)
    print("DELTA LAKE ANALYSIS")
    print("=" * 70)

    # Load all data
    df = pl.read_delta(str(delta_path))

    print(f"\nTotal articles: {len(df):,}")
    print(f"Columns: {', '.join(df.columns)}")

    # By domain
    print("\n📊 Articles by domain:")
    domain_counts = df.group_by("source_domain").len().sort("source_domain")
    for row in domain_counts.iter_rows():
        print(f"  {row[0]}: {row[1]:,}")

    # By crawl
    print("\n📅 Articles by crawl:")
    crawl_counts = df.group_by("crawl_id").len().sort("crawl_id")
    for row in crawl_counts.iter_rows():
        print(f"  {row[0]}: {row[1]:,}")

    # By domain+crawl combination
    print("\n🗂️  Articles by domain + crawl:")
    combo_counts = df.group_by(["source_domain", "crawl_id"]).len().sort(["source_domain", "crawl_id"])
    for row in combo_counts.iter_rows():
        print(f"  {row[1]} + {row[0]}: {row[2]:,}")

    # Date range
    if df["timestamp"].is_not_null().any():
        print("\n📆 Date range:")
        print(f"  Earliest: {df['timestamp'].min()}")
        print(f"  Latest: {df['timestamp'].max()}")

    return df


def analyze_progress():
    """Analyze progress tracking."""
    checkpoint_file = Path(settings.database.checkpoint_file)

    print("\n" + "=" * 70)
    print("PROGRESS TRACKING")
    print("=" * 70)

    if not checkpoint_file.exists():
        print("No checkpoint file found!")
        return

    with open(checkpoint_file) as f:
        checkpoint = json.load(f)

    completed = checkpoint.get("completed_crawl_domain_pairs", [])
    total_inserted = checkpoint.get("total_articles_inserted", 0)

    print(f"\nCompleted crawl-domain pairs: {len(completed)}")
    print(f"Total articles inserted: {total_inserted:,}")
    print(f"Last updated: {checkpoint.get('last_updated', 'N/A')}")

    # Calculate what's missing
    all_combinations = []
    for crawl_id in settings.crawls.crawl_ids:
        for domain in settings.news_sources.domains:
            all_combinations.append((crawl_id, domain))

    completed_set = set(completed)
    missing = [(c, d) for c, d in all_combinations if f"{c}:{d}" not in completed_set]

    print(f"\n📋 Total combinations: {len(all_combinations)} ({len(settings.crawls.crawl_ids)} crawls × {len(settings.news_sources.domains)} domains)")
    print(f"✅ Completed: {len(completed)}")
    print(f"❌ Missing: {len(missing)}")

    # Show missing by crawl
    print("\n❌ Missing by crawl:")
    for crawl_id in settings.crawls.crawl_ids:
        crawl_missing = [d for c, d in missing if c == crawl_id]
        if crawl_missing:
            print(f"  {crawl_id}: {len(crawl_missing)} domains")
            for d in crawl_missing[:3]:
                print(f"    - {d}")
            if len(crawl_missing) > 3:
                print(f"    ... and {len(crawl_missing) - 3} more")

    return missing


def main():
    """Main analysis."""
    print(f"\nAnalysis run at: {datetime.now().isoformat()}\n")

    df = analyze_delta_lake()
    missing = analyze_progress()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if df is not None:
        print(f"✅ Delta Lake: {len(df):,} articles stored")

    if missing:
        print(f"❌ Still need to process: {len(missing)} crawl-domain pairs")
        print("\nTo resume processing:")
        print("  cd /opt/data/workspace/covid-nz-news")
        print("  uv run build_database.py  # Will auto-resume from checkpoint")


if __name__ == "__main__":
    main()
