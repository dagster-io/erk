"""
Test cases for data retention and cleanup.

Tests persistence, timestamp handling, and data retention policies.
"""

import asyncio

import pytest

from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.schema_changes import SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory


class TestUsageTrackingDataRetention:
    """Test cases for data retention and cleanup."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.conn_factory = SqliteConnectionFactory.temporary_for_testing()
        self.analytics_store = SlackbotAnalyticsStore(self.conn_factory)

        # Apply schema changes
        with self.conn_factory.with_conn() as conn:
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)

    @pytest.mark.asyncio
    async def test_usage_tracking_persists_across_sessions(self):
        """Test that usage tracking data persists across sessions."""
        # Create initial data
        await self.analytics_store.increment_answer_count("persistent_bot")
        await self.analytics_store.increment_answer_count("persistent_bot")

        # Create new analytics store instance (simulating restart)
        new_analytics_store = SlackbotAnalyticsStore(self.conn_factory)

        # Data should still be there
        data = await new_analytics_store.get_usage_tracking_data(
            "persistent_bot", include_bonus_answers=True
        )
        assert len(data) == 1
        assert data[0]["answer_count"] == 2

        # Should be able to continue incrementing
        await new_analytics_store.increment_answer_count("persistent_bot")

        # Verify count is now 3
        data = await new_analytics_store.get_usage_tracking_data(
            "persistent_bot", include_bonus_answers=True
        )
        assert data[0]["answer_count"] == 3

    @pytest.mark.asyncio
    async def test_timestamps_are_updated_correctly(self):
        """Test that timestamps are updated correctly."""
        bot_id = "timestamp_test_bot"

        # First increment
        await self.analytics_store.increment_answer_count(bot_id)
        data1 = await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )

        # Longer delay to ensure timestamp difference (SQLite has second precision)
        await asyncio.sleep(1.1)

        # Second increment
        await self.analytics_store.increment_answer_count(bot_id)
        data2 = await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )

        # Verify timestamps are different
        assert data1[0]["updated_at"] != data2[0]["updated_at"]
        # Created timestamp should stay the same
        assert data1[0]["created_at"] == data2[0]["created_at"]
        # Answer count should be incremented
        assert data2[0]["answer_count"] == 2
