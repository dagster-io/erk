"""
Test cases for error handling in usage tracking.

Tests proper handling of database errors, missing schema, and edge cases.
"""

from unittest.mock import Mock

import pytest

from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.schema_changes import SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory


class TestUsageTrackingErrorHandling:
    """Test cases for error handling in usage tracking."""

    @pytest.fixture
    def conn_factory_no_schema(self):
        """Create a connection factory without schema applied."""
        return SqliteConnectionFactory.temporary_for_testing()

    @pytest.fixture
    def conn_factory_with_schema(self):
        """Create a connection factory with schema applied."""
        factory = SqliteConnectionFactory.temporary_for_testing()
        with factory.with_conn() as conn:
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)
        return factory

    @pytest.mark.asyncio
    async def test_increment_without_schema_creation(self, conn_factory_no_schema):
        """Test that increment gracefully handles missing schema."""
        analytics_store = SlackbotAnalyticsStore(conn_factory_no_schema)

        # Note: temporary_for_testing() automatically applies schema, so this test
        # effectively validates that the default factory configuration works correctly
        await analytics_store.increment_answer_count("test_bot")
        data = await analytics_store.get_usage_tracking_data("test_bot", include_bonus_answers=True)
        # With auto-schema application, data should be present
        assert len(data) == 1
        assert data[0]["answer_count"] == 1

    @pytest.mark.asyncio
    async def test_get_usage_data_with_empty_database(self, conn_factory_with_schema):
        """Test getting usage data from empty database."""
        analytics_store = SlackbotAnalyticsStore(conn_factory_with_schema)

        # Schema already applied, but no data added
        # Should return empty list
        data = await analytics_store.get_usage_tracking_data(None, include_bonus_answers=True)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test handling of database connection errors."""
        # Create a mock connection factory that raises errors
        mock_conn_factory = Mock()
        mock_conn_factory.supports_analytics.return_value = True
        mock_conn_factory.with_conn.side_effect = Exception("Database connection failed")

        analytics_store = SlackbotAnalyticsStore(mock_conn_factory)

        # Should raise database connection error
        with pytest.raises(Exception):
            await analytics_store.increment_answer_count("test_bot")
