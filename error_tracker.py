"""Error tracking and reporting for the build process."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ErrorRecord:
    """Single error record."""
    error_type: str
    message: str
    context: Dict[str, str] = field(default_factory=dict)


class ErrorTracker:
    """Track and report errors during the build process."""

    def __init__(self, logger: logging.Logger):
        """
        Initialize error tracker.

        Args:
            logger: Logger instance for logging
        """
        self.logger = logger
        self.errors: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}

    def track(self, error_type: str, message: str, **context) -> None:
        """
        Track an error.

        Args:
            error_type: Type/category of error (e.g., 'download_failed', 'extraction_error')
            message: Error message
            **context: Additional context (e.g., url=..., filename=...)
        """
        record = ErrorRecord(error_type=error_type, message=message, context=context)
        self.errors.append(record)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def report(self) -> None:
        """
        Report all tracked errors at the end of the build process.
        """
        if not self.errors:
            self.logger.info("No errors encountered during build.")
            return

        self.logger.info("=" * 70)
        self.logger.info("ERROR SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Total errors: {len(self.errors)}")

        # Group by type
        self.logger.info("\nErrors by type:")
        for error_type, count in sorted(self.error_counts.items(), key=lambda x: -x[1]):
            self.logger.info(f"  {error_type}: {count}")

        # Show sample errors (up to 5 per type)
        self.logger.info("\nSample errors (up to 5 per type):")
        shown_types = set()
        for record in self.errors:
            if record.error_type in shown_types:
                continue
            self.logger.info(f"\n  {record.error_type}:")
            self.logger.info(f"    Message: {record.message}")
            if record.context:
                self.logger.info(f"    Context: {record.context}")
            shown_types.add(record.error_type)
            if len(shown_types) >= 5:
                break

        self.logger.info("=" * 70)

    def get_count(self) -> int:
        """Get total error count."""
        return len(self.errors)

    def get_by_type(self, error_type: str) -> List[ErrorRecord]:
        """Get all errors of a specific type."""
        return [e for e in self.errors if e.error_type == error_type]
