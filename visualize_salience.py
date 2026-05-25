"""Visualize COVID salience timeline from the news database.

Generates plots showing:
1. Daily article counts over time
2. Article counts by news source
3. Daily article counts by source (stacked area chart)

Usage:
    uv run visualize_salience.py [--db-path covid_nz_news.db] [--output-dir ./exports]
"""
import argparse
import os

import polars as pl

from database import NewsDatabase
from salience_metrics import SalienceMetrics


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize COVID salience metrics from database'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='covid_nz_news.db',
        help='Path to SQLite database (default: covid_nz_news.db)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='exports',
        help='Output directory for plot files (default: exports)'
    )
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Connect to database
    print(f"Connecting to database: {args.db_path}")
    db = NewsDatabase(args.db_path)
    db.connect()

    # Calculate metrics
    print("Calculating salience metrics...")
    metrics = SalienceMetrics(db)

    # Get statistics
    stats = metrics.get_total_statistics()
    print(f"\nDatabase statistics:")
    print(f"  Total articles: {stats['total_articles']:,}")
    print(f"  Unique sources: {stats['unique_sources']}")
    print(f"  Date range: {stats['date_earliest']} to {stats['date_latest']}")
    print(f"  Days covered: {stats['days_covered']}")

    # Check if we have data
    if stats['total_articles'] == 0:
        print("\nNo data in database. Run build_database.py first.")
        db.close()
        return

    # Create plots
    print("\nGenerating visualizations...")

    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import pandas as pd
    except ImportError as e:
        print(f"Visualization libraries not installed: {e}")
        print("Install with: uv pip install matplotlib plotnine")
        db.close()
        return

    # Plot 1: Timeline
    create_timeline_plot(metrics, args.output_dir)

    # Plot 2: Source comparison
    create_source_comparison_plot(metrics, args.output_dir)

    # Plot 3: Stacked timeline
    create_stacked_timeline_plot(metrics, args.output_dir)

    db.close()

    print(f"\nAll visualizations saved to {args.output_dir}/")
    print("Generated files:")
    print(f"  - {args.output_dir}/covid_salience_timeline.png")
    print(f"  - {args.output_dir}/articles_by_source.png")
    print(f"  - {args.output_dir}/stacked_timeline_by_source.png")


def create_timeline_plot(metrics: SalienceMetrics, output_dir: str):
    """Create daily article count timeline plot."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd

    daily_df = metrics.get_articles_per_day()

    if len(daily_df) == 0:
        print("No data available for timeline plot")
        return

    # Convert to pandas for plotting
    df = daily_df.to_pandas()

    # Parse dates
    df['date'] = pd.to_datetime(df['date'])

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), dpi=100)

    # Top plot: Daily article counts
    ax1 = axes[0]
    ax1.plot(df['date'], df['article_count'], 'b-', linewidth=1.5, alpha=0.7)
    ax1.fill_between(df['date'], df['article_count'], alpha=0.3, color='blue')
    ax1.set_ylabel('Articles per day', fontsize=12)
    ax1.set_title('NZ COVID News Coverage Timeline', fontsize=14, fontweight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.grid(True, alpha=0.3)

    # Rotate x labels
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Bottom plot: Rolling 7-day average
    ax2 = axes[1]
    rolling_avg = df['article_count'].rolling(window=7).mean()
    ax2.plot(df['date'], rolling_avg, 'g-', linewidth=2, alpha=0.8)
    ax2.fill_between(df['date'], rolling_avg, alpha=0.3, color='green')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('7-day rolling average', fontsize=12)
    ax2.set_title('Smoothed Trend', fontsize=12)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.grid(True, alpha=0.3)

    # Rotate x labels
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save
    output_path = os.path.join(output_dir, 'covid_salience_timeline.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"Saved timeline plot to {output_path}")
    plt.close()


def create_source_comparison_plot(metrics: SalienceMetrics, output_dir: str):
    """Create bar chart comparing article counts by source."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    source_df = metrics.get_articles_per_source()

    if len(source_df) == 0:
        print("No data available for source comparison plot")
        return

    df = source_df.to_pandas()

    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

    colors = plt.cm.Set3(range(len(df)))
    bars = ax.bar(df['source_domain'], df['article_count'], color=colors, alpha=0.8)

    ax.set_ylabel('Number of articles', fontsize=12)
    ax.set_xlabel('News source', fontsize=12)
    ax.set_title('COVID Articles by News Source', fontsize=14, fontweight='bold')

    # Rotate x labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Add value labels on bars
    for bar, count in zip(bars, df['article_count']):
        height = bar.get_height()
        ax.annotate(f'{count:,}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords='offset points',
                    ha='center', va='bottom', fontsize=9)

    ax.grid(axis='y', alpha=0.3)

    # Save
    output_path = os.path.join(output_dir, 'articles_by_source.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"Saved source comparison plot to {output_path}")
    plt.close()


def create_stacked_timeline_plot(metrics: SalienceMetrics, output_dir: str):
    """Create stacked area chart showing articles per source per day."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd

    daily_source_df = metrics.get_articles_per_source_per_day()

    if len(daily_source_df) == 0:
        print("No data available for stacked timeline plot")
        return

    df = daily_source_df.to_pandas()

    # Parse dates
    df['date'] = pd.to_datetime(df['date'])

    # Pivot for stacked area chart
    pivot_df = df.pivot(index='date', columns='source_domain', values='article_count').fillna(0)

    fig, ax = plt.subplots(figsize=(14, 7), dpi=100)

    # Create stacked area chart
    pivot_df.plot.area(ax=ax, linewidth=0, alpha=0.8)
    ax.set_ylabel('Articles per day', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_title('Daily COVID Articles by News Source', fontsize=14, fontweight='bold')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.grid(True, alpha=0.3)

    # Rotate x labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save
    output_path = os.path.join(output_dir, 'stacked_timeline_by_source.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"Saved stacked timeline plot to {output_path}")
    plt.close()


if __name__ == '__main__':
    main()
