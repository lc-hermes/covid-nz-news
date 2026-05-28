"""Export COVID NZ News database to HuggingFace dataset format.

This script exports the Delta Lake database to HuggingFace dataset format
and optionally pushes it to the HuggingFace Hub.

Usage:
    uv run export_huggingface.py [--push] [--repo-name <name>]

Environment variables:
    HF_TOKEN: Your HuggingFace API token (required for push)

Example:
    # Export locally
    uv run export_huggingface.py

    # Push to HuggingFace Hub
    HF_TOKEN=your_token uv run export_huggingface.py --push
"""

import os
from pathlib import Path

import polars as pl
from datasets import Dataset


def load_delta_table(table_path: str) -> pl.DataFrame:
    """Load data from Delta Lake table."""
    df = pl.scan_delta(table_path).collect()
    print(f"Loaded {len(df)} articles from Delta Lake table")
    return df


def convert_to_huggingface_format(df: pl.DataFrame) -> Dataset:
    """Convert Polars DataFrame to HuggingFace Dataset."""
    print(f"Converting {len(df)} records to HuggingFace format...")

    # Convert Polars DataFrame to list of dicts
    records = df.to_dicts()

    # Create HuggingFace Dataset
    dataset = Dataset.from_list(records)

    print(f"Created HuggingFace Dataset with {len(dataset)} examples")
    print(f"Features: {dataset.features}")

    return dataset


def save_dataset_locally(dataset: Dataset, output_path: str = "covid_nz_news_dataset"):
    """Save dataset locally in HuggingFace format."""
    print(f"Saving dataset to {output_path}...")
    dataset.save_to_disk(output_path)
    print(f"Dataset saved to {output_path}")


def push_to_hub(dataset: Dataset, repo_name: str = "lc-hermes/covid-nz-news", token: str | None = None) -> None:
    """Push dataset to HuggingFace Hub."""
    if token is None:
        token = os.environ.get("HF_TOKEN")
        if token is None:
            raise ValueError(
                "HF_TOKEN environment variable not set. "
                "Get your token from https://huggingface.co/settings/tokens"
            )

    print(f"Pushing dataset to {repo_name}...")

    # Push to Hub
    dataset.push_to_hub(
        repo_id=repo_name,
        token=token,
        private=False,  # Set to True for private repo
        commit_message="Add COVID NZ News dataset",
    )

    print(f"Dataset pushed to https://huggingface.co/datasets/{repo_name}")


def main():
    """Main export function."""
    import argparse

    parser = argparse.ArgumentParser(description="Export COVID NZ News to HuggingFace dataset")
    parser.add_argument("--push", action="store_true", help="Push to HuggingFace Hub")
    parser.add_argument("--repo-name", default="lc-hermes/covid-nz-news",
                       help="HuggingFace repo name (default: lc-hermes/covid-nz-news)")
    parser.add_argument("--table-path", default="covid_nz_news_delta",
                       help="Path to Delta Lake table (default: covid_nz_news_delta)")
    parser.add_argument("--output-path", default="covid_nz_news_dataset",
                       help="Local output path (default: covid_nz_news_dataset)")

    args = parser.parse_args()

    # Load data
    df = load_delta_table(args.table_path)

    if len(df) == 0:
        print("WARNING: Database is empty! No data to export.")
        print("Run build_database.py to collect articles from Common Crawl first.")
        return

    # Convert to HuggingFace format
    dataset = convert_to_huggingface_format(df)

    # Save locally
    save_dataset_locally(dataset, args.output_path)

    # Optionally push to Hub
    if args.push:
        push_to_hub(dataset, args.repo_name)


if __name__ == "__main__":
    main()
