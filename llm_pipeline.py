"""LLM classification pipeline for COVID NZ News articles.

This script classifies articles from the Delta Lake database into categories
using a local LLM server.

Usage:
    uv run llm_pipeline.py [--limit N] [--resume] [--no-resume]

Example:
    # Classify first 100 articles
    uv run llm_pipeline.py --limit 100

    # Process all articles, resuming from existing classifications
    uv run llm_pipeline.py --resume
"""

import argparse
from pathlib import Path

import polars as pl
from tqdm import tqdm

from delta_database import DeltaNewsDatabase
from llm_client import LLMClient
from llm_config import PipelineConfig


def load_articles(config: PipelineConfig) -> pl.DataFrame:
    """Load articles from Delta Lake table."""
    # Load directly using Polars
    df = pl.scan_delta(config.input_path).collect()

    # Apply filter if specified
    if config.input_filter:
        df = df.filter(pl.col(config.input_filter))

    # Apply limit if specified
    if config.limit:
        df = df.limit(config.limit)

    print(f"Loaded {len(df)} articles from Delta Lake table")
    return df


def load_existing_classifications(output_path: str) -> dict[str, str]:
    """Load existing classifications from parquet file."""
    if not Path(output_path).exists():
        return {}

    df = pl.read_parquet(output_path)
    classifications = dict(zip(df["url"], df["category"], strict=False))
    print(f"Loaded {len(classifications)} existing classifications")
    return classifications


def run_pipeline(config: PipelineConfig) -> None:
    """Run the classification pipeline."""
    # Initialize client
    client = LLMClient(config)

    # Load articles
    df = load_articles(config)

    if len(df) == 0:
        print("No articles to classify!")
        return

    # Load existing classifications if resuming
    existing = {}
    if config.resume:
        existing = load_existing_classifications(config.classification.output_path)

    # Filter out already classified articles
    if existing:
        urls_to_classify = [url for url in df["url"] if url not in existing]
        df = df.filter(pl.col("url").is_in(urls_to_classify))
        print(f"Filtered to {len(df)} articles (excluding {len(existing)} already classified)")

    if len(df) == 0:
        print("All articles already classified!")
        return

    # Prepare data for classification
    articles = df.select(["url", "title", "content"]).to_dicts()
    categories = config.classification.categories

    # Classify in batches
    classifications = existing.copy()

    for i in tqdm(range(0, len(articles), config.classification.batch_size)):
        batch = articles[i : i + config.classification.batch_size]

        for article, category in zip(batch, client.batch_classify(batch, categories), strict=False):
            url = article["url"]
            classifications[url] = category

    # Save results
    output_df = pl.DataFrame([
        {"url": url, "category": cat}
        for url, cat in classifications.items()
    ])

    # Merge with original data for richer output
    original_df = load_articles(config)
    result_df = original_df.join(
        output_df,
        on="url",
        how="left"
    )

    output_path = config.classification.output_path
    result_df.write_parquet(output_path)
    print(f"Saved {len(result_df)} classifications to {output_path}")

    # Print summary
    category_counts = result_df.group_by("category").agg(
        pl.col("url").count().alias("count")
    ).sort("count", descending=True)

    print("\nClassification summary:")
    for row in category_counts.iter_rows():
        print(f"  {row[0]}: {row[1]}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LLM classification pipeline for COVID NZ News")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of articles to process")
    parser.add_argument("--resume", action="store_true", default=True,
                       help="Resume from existing classifications")
    parser.add_argument("--no-resume", action="store_false", dest="resume",
                       help="Don't resume, start fresh")
    parser.add_argument("--output", type=str, default="llm_classifications.parquet",
                       help="Output parquet file path")
    parser.add_argument("--llm-url", type=str, default="http://localhost:8000",
                       help="LLM server URL")
    parser.add_argument("--model", type=str, default="default",
                       help="LLM model name")

    args = parser.parse_args()

    # Build config
    config = PipelineConfig(
        input_path="covid_nz_news_delta",
        limit=args.limit,
        resume=args.resume,
    )
    config.llm.base_url = args.llm_url
    config.llm.model = args.model
    config.classification.output_path = args.output

    # Run pipeline
    run_pipeline(config)


if __name__ == "__main__":
    main()
