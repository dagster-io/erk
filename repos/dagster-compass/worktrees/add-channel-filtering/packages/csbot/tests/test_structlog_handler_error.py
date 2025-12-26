"""Test to reproduce the structlog addHandler AttributeError."""

from unittest.mock import MagicMock

import pytest
import structlog

from csbot.slackbot.channel_bot.bot import SlackLoggingHandler


class TestStructlogHandlerError:
    """Test cases for reproducing the structlog addHandler error."""

    def test_structlog_logger_has_no_addhandler_method(self):
        """
        Test that reproduces the exact error:
        'BoundLoggerFilteringAtInfo' object has no attribute 'addHandler'

        This test demonstrates the bug in the admin command handling where
        structlog logger is being used as if it were a stdlib logger.
        """
        # Create mock Slack components
        mock_client = MagicMock()
        origin_channel = "C1234567890"
        origin_message_ts = "1234567890.123456"

        # Get structlog logger (this is what the code does)
        child_logger = structlog.get_logger()

        # Verify this is not a stdlib logger
        assert not hasattr(child_logger, "addHandler"), (
            f"structlog logger {type(child_logger)} should not have addHandler method"
        )

        # Create SlackLoggingHandler
        slack_handler = SlackLoggingHandler(
            mock_client,
            origin_channel,
            origin_message_ts,
        )

        # This should raise AttributeError - exactly what the user reported
        with pytest.raises(AttributeError, match="object has no attribute 'addHandler'"):
            child_logger.addHandler(slack_handler)

    def test_reproduce_exact_error_message(self):
        """Reproduce the exact error message from the user report."""
        mock_client = MagicMock()
        child_logger = structlog.get_logger()
        slack_handler = SlackLoggingHandler(mock_client, "C123", "123.456")

        try:
            child_logger.addHandler(slack_handler)
            pytest.fail("Expected AttributeError was not raised")
        except AttributeError as e:
            error_msg = str(e)
            print(f"Exact error message: {error_msg}")
            # Verify it contains the key parts from user report
            assert "object has no attribute 'addHandler'" in error_msg
            assert "BoundLogger" in error_msg or "Bound" in error_msg

    def test_slack_logging_handler_is_stdlib_handler(self):
        """Verify that SlackLoggingHandler is designed for stdlib logging."""
        import logging

        mock_client = MagicMock()
        origin_channel = "C1234567890"
        origin_message_ts = "1234567890.123456"

        handler = SlackLoggingHandler(mock_client, origin_channel, origin_message_ts)

        # SlackLoggingHandler should be a stdlib Handler
        assert isinstance(handler, logging.Handler)

        # It should work with stdlib logger
        stdlib_logger = logging.getLogger("test_logger")
        stdlib_logger.addHandler(handler)  # This should not raise

        # Cleanup
        stdlib_logger.removeHandler(handler)

    def test_structlog_vs_stdlib_logger_types(self):
        """Document the difference between structlog and stdlib loggers."""
        import logging

        # Get both types of loggers
        structlog_logger = structlog.get_logger()
        stdlib_logger = logging.getLogger("test")

        # They are different types
        assert not isinstance(structlog_logger, type(stdlib_logger))

        # stdlib logger has addHandler, structlog logger does not
        assert hasattr(stdlib_logger, "addHandler")
        assert not hasattr(structlog_logger, "addHandler")

        # Document the actual types for debugging
        print(f"structlog logger type: {type(structlog_logger)}")
        print(f"stdlib logger type: {type(stdlib_logger)}")

    def test_fixed_approach_works(self):
        """Test that the fixed approach using stdlib logger works."""
        import logging

        mock_client = MagicMock()
        origin_channel = "C1234567890"
        origin_message_ts = "1234567890.123456"

        # This is the fixed approach - use stdlib logger instead of structlog logger
        stdlib_logger = logging.getLogger()  # Use stdlib logger for handler management

        # Create and add the handler to stdlib logger - this should work
        slack_handler = SlackLoggingHandler(
            mock_client,
            origin_channel,
            origin_message_ts,
        )

        # This should not raise any error
        stdlib_logger.addHandler(slack_handler)

        # Verify handler was added
        assert slack_handler in stdlib_logger.handlers

        # Cleanup
        stdlib_logger.removeHandler(slack_handler)
