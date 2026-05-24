"""Unit tests for logger module."""
import logging

from logger import setup_logging


class TestLogger:
    """Test logger functionality."""

    def test_setup_logging_returns_logger(self):
        """Setup logging should return a logger instance."""
        logger = setup_logging(log_level='INFO', log_file=None, console_output=False)
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'covid_nz_news'

    def test_setup_logging_with_valid_level(self):
        """Setup logging should accept valid log levels."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            logger = setup_logging(log_level=level, log_file=None, console_output=False)
            assert logger.level == getattr(logging, level)

    def test_setup_logging_invalid_level_defaults_to_info(self):
        """Setup logging should default to INFO for invalid levels."""
        logger = setup_logging(log_level='INVALID', log_file=None, console_output=False)
        assert logger.level == logging.INFO

    def test_logger_can_log(self, tmp_path):
        """Logger should be able to log messages."""
        log_file = tmp_path / 'test.log'
        logger = setup_logging(log_level='INFO', log_file=str(log_file), console_output=False)
        logger.info('Test message')
        assert log_file.exists()
        assert 'Test message' in log_file.read_text()
