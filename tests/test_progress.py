"""Unit tests for progress tracking."""
import json

from progress import ProgressManager, ProgressState


class TestProgressState:
    """Tests for ProgressState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = ProgressState()
        assert state.completed_crawl_domain_pairs == []
        assert state.total_articles_inserted == 0
        assert state.last_updated == ''

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = ProgressState(
            completed_crawl_domain_pairs=['crawl1:domain1', 'crawl2:domain2'],
            total_articles_inserted=100,
            last_updated='2024-01-01T00:00:00'
        )
        data = state.to_dict()
        assert data['completed_crawl_domain_pairs'] == ['crawl1:domain1', 'crawl2:domain2']
        assert data['total_articles_inserted'] == 100
        assert data['last_updated'] == '2024-01-01T00:00:00'

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'completed_crawl_domain_pairs': ['crawl1:domain1'],
            'total_articles_inserted': 50,
            'last_updated': '2024-01-01'
        }
        state = ProgressState.from_dict(data)
        assert state.completed_crawl_domain_pairs == ['crawl1:domain1']
        assert state.total_articles_inserted == 50
        assert state.last_updated == '2024-01-01'


class TestProgressManager:
    """Tests for ProgressManager class."""

    def test_init(self, tmp_path):
        """Test initialization."""
        checkpoint_file = tmp_path / 'progress.json'
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        assert manager.checkpoint_file == checkpoint_file
        assert manager.state is None

    def test_load_no_file(self, tmp_path):
        """Test loading when no checkpoint file exists."""
        checkpoint_file = tmp_path / 'progress.json'
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        state = manager.load()
        assert state is None

    def test_load_valid_file(self, tmp_path):
        """Test loading from valid checkpoint file."""
        checkpoint_file = tmp_path / 'progress.json'
        checkpoint_file.write_text(json.dumps({
            'completed_crawl_domain_pairs': ['crawl1:domain1'],
            'total_articles_inserted': 100,
            'last_updated': '2024-01-01'
        }))

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        state = manager.load()

        assert state is not None
        assert state.completed_crawl_domain_pairs == ['crawl1:domain1']
        assert state.total_articles_inserted == 100

    def test_load_invalid_json(self, tmp_path):
        """Test loading from invalid JSON file."""
        checkpoint_file = tmp_path / 'progress.json'
        checkpoint_file.write_text('invalid json')

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        state = manager.load()

        assert state is None

    def test_save(self, tmp_path):
        """Test saving progress state."""
        checkpoint_file = tmp_path / 'progress.json'
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))

        state = ProgressState(
            completed_crawl_domain_pairs=['crawl1:domain1'],
            total_articles_inserted=50,
            last_updated='2024-01-01'
        )

        result = manager.save(state)
        assert result is True
        assert checkpoint_file.exists()

        loaded_data = json.loads(checkpoint_file.read_text())
        assert loaded_data['total_articles_inserted'] == 50

    def test_clear(self, tmp_path):
        """Test clearing checkpoint file."""
        checkpoint_file = tmp_path / 'progress.json'
        checkpoint_file.write_text('{}')

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        result = manager.clear()

        assert result is True
        assert not checkpoint_file.exists()

    def test_is_completed(self, tmp_path):
        """Test checking if crawl-domain pair is completed."""
        checkpoint_file = tmp_path / 'progress.json'
        checkpoint_file.write_text(json.dumps({
            'completed_crawl_domain_pairs': ['crawl1:domain1', 'crawl2:domain2'],
            'total_articles_inserted': 100,
            'last_updated': '2024-01-01'
        }))

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        manager.load()

        assert manager.is_completed('crawl1', 'domain1') is True
        assert manager.is_completed('crawl2', 'domain2') is True
        assert manager.is_completed('crawl3', 'domain3') is False

    def test_mark_completed(self, tmp_path):
        """Test marking crawl-domain pair as completed."""
        checkpoint_file = tmp_path / 'progress.json'
        manager = ProgressManager(checkpoint_file=str(checkpoint_file))

        result = manager.mark_completed('crawl1', 'domain1', 10)
        assert result is True
        assert manager.state is not None
        assert manager.state.total_articles_inserted == 10
        assert 'crawl1:domain1' in manager.state.completed_crawl_domain_pairs

    def test_get_remaining_work(self, tmp_path):
        """Test getting remaining work."""
        checkpoint_file = tmp_path / 'progress.json'
        checkpoint_file.write_text(json.dumps({
            'completed_crawl_domain_pairs': ['crawl1:domain1'],
            'total_articles_inserted': 10,
            'last_updated': '2024-01-01'
        }))

        manager = ProgressManager(checkpoint_file=str(checkpoint_file))
        manager.load()

        all_crawls = ['crawl1', 'crawl2']
        all_domains = ['domain1', 'domain2']

        remaining = manager.get_remaining_work(all_crawls, all_domains)

        # Should have 3 remaining (crawl1:domain2, crawl2:domain1, crawl2:domain2)
        assert len(remaining) == 3
        assert ('crawl1', 'domain2') in remaining
        assert ('crawl2', 'domain1') in remaining
        assert ('crawl2', 'domain2') in remaining
        assert ('crawl1', 'domain1') not in remaining
