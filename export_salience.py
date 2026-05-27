"""Export salience metrics to CSV."""

import argparse
import csv
import logging
from typing import List, Optional

from delta_database import DeltaNewsDatabase
from salience_metrics import SalienceMetrics


def export_salience_metrics(
    db_path: str,
    output_file: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Export salience metrics to CSV file.

    Args:
        db_path: Path to Delta Lake table
        output_file: Output CSV file path
        logger: Logger instance
    """
    log = logger or logging.getLogger("covid_nz_news.export_salience")

    # Initialize database
    db = DeltaNewsDatabase(db_path, logger=log)
    metrics = SalienceMetrics(db, logger=log)

    log.info(f"Exporting salience metrics to {output_file}")

    # Calculate all metrics
    source_salience = metrics.get_source_salience()
    language_salience = metrics.get_language_salience()
    temporal_salience = metrics.get_temporal_salience()

    # Write to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Source salience
        writer.writerow(["# Source Salience"])
        if source_salience:
            writer.writerow(source_salience.keys())
            for row in zip(*source_salience.values(), strict=False):
                writer.writerow(row)

        writer.writerow([])  # Empty row

        # Language salience
        writer.writerow(["# Language Salience"])
        if language_salience:
            writer.writerow(language_salience.keys())
            for row in zip(*language_salience.values(), strict=False):
                writer.writerow(row)

        writer.writerow([])  # Empty row

        # Temporal salience
        writer.writerow(["# Temporal Salience"])
        if temporal_salience:
            writer.writerow(temporal_salience.keys())
            for row in zip(*temporal_salience.values(), strict=False):
                writer.writerow(row)

    log.info(f"Exported salience metrics to {output_file}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export salience metrics to CSV")
    parser.add_argument(
        "--db-path",
        default="covid_nz_news_delta",
        help="Path to Delta Lake table",
    )
    parser.add_argument(
        "--output",
        default="salience_metrics.csv",
        help="Output CSV file path",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    export_salience_metrics(args.db_path, args.output)


if __name__ == "__main__":
    main()
