"""Progress tracking for COVID NZ News database building.

Saves checkpoint state to allow resuming interrupted database builds.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ProgressState:
    """Represents the current progress of the database build."""

    completed_crawl_domain_pairs: List[str] = field(default_factory=list)
    completed_warc_files: List[str] = field(default_factory=list)
    total_articles_inserted: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "completed_crawl_domain_pairs": self.completed_crawl_domain_pairs,
            "completed_warc_files": self.completed_warc_files,
            "total_articles_inserted": self.total_articles_inserted,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ProgressState":
        """Create instance from dictionary."""
        return cls(**data)


class ProgressManager:
    """Manages progress checkpointing for database builds."""

    def __init__(
        self, checkpoint_file: str = "build_progress.json", logger: Optional[logging.Logger] = None
    ):
        """
        Initialize progress manager.

        Args:
            checkpoint_file: Path to JSON file for storing progress
            logger: Logger instance
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.logger = logger or logging.getLogger("covid_nz_news.progress")
        self.state: Optional[ProgressState] = None

    def load(self) -> Optional[ProgressState]:
        """
        Load progress state from file.

        Returns:
            ProgressState if file exists, None otherwise
        """
        if not self.checkpoint_file.exists():
            self.logger.info(f"No checkpoint file found at {self.checkpoint_file}")
            return None

        try:
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
            self.state = ProgressState.from_dict(data)
            self.logger.info(
                f"Loaded progress: {self.state.total_articles_inserted} articles from checkpoint"
            )
            return self.state
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse checkpoint file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {type(e).__name__}: {e}")
            return None

    def save(self, state: ProgressState) -> bool:
        """
        Save progress state to file.

        Args:
            state: Progress state to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.state = state
            with open(self.checkpoint_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            self.logger.info(f"Saved checkpoint: {state.total_articles_inserted} articles")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {type(e).__name__}: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear checkpoint file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                self.logger.info("Cleared checkpoint file")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {type(e).__name__}: {e}")
            return False

    def is_completed(self, crawl_id: str, domain: str) -> bool:
        """
        Check if a specific crawl-domain pair is already completed.

        Args:
            crawl_id: Crawl ID to check
            domain: Domain to check

        Returns:
            True if already completed, False otherwise
        """
        if not self.state:
            return False

        key = f"{crawl_id}:{domain}"
        return key in self.state.completed_crawl_domain_pairs

    def mark_completed(self, crawl_id: str, domain: str, articles_inserted: int) -> bool:
        """
        Mark a crawl-domain pair as completed.

        Args:
            crawl_id: Crawl ID
            domain: Domain
            articles_inserted: Number of articles inserted for this pair

        Returns:
            True if successful, False otherwise
        """
        if not self.state:
            self.state = ProgressState()

        key = f"{crawl_id}:{domain}"
        if key not in self.state.completed_crawl_domain_pairs:
            self.state.completed_crawl_domain_pairs.append(key)

        self.state.total_articles_inserted += articles_inserted
        from datetime import datetime

        self.state.last_updated = datetime.now().isoformat()

        return self.save(self.state)

    def mark_warc_completed(self, warc_filename: str) -> bool:
        """
        Mark a WARC file as completed.

        Args:
            warc_filename: WARC file path/hash

        Returns:
            True if successful, False otherwise
        """
        if not self.state:
            self.state = ProgressState()

        if warc_filename not in self.state.completed_warc_files:
            self.state.completed_warc_files.append(warc_filename)
            from datetime import datetime

            self.state.last_updated = datetime.now().isoformat()

        return self.save(self.state)

    def is_warc_completed(self, warc_filename: str) -> bool:
        """
        Check if a WARC file has already been processed.

        Args:
            warc_filename: WARC file path/hash

        Returns:
            True if already completed, False otherwise
        """
        if not self.state:
            return False

        return warc_filename in self.state.completed_warc_files

    def get_remaining_work(self, all_crawls: List[str], all_domains: List[str]) -> List[tuple]:
        """
        Get list of crawl-domain pairs that still need to be processed.

        Args:
            all_crawls: List of all crawl IDs
            all_domains: List of all domains

        Returns:
            List of (crawl_id, domain) tuples that are not yet completed
        """
        remaining = []
        for crawl_id in all_crawls:
            for domain in all_domains:
                if not self.is_completed(crawl_id, domain):
                    remaining.append((crawl_id, domain))
        return remaining
