"""
Test cases for the UsageTracker wrapper class.

Tests the high-level UsageTracker interface for usage monitoring operations.
"""

import pytest

from csbot.slackbot.storage.schema_changes import SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory
from csbot.slackbot.usage_tracking import UsageTracker


class TestUsageTracker:
    """Test cases for the UsageTracker wrapper class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.conn_factory = SqliteConnectionFactory.temporary_for_testing()
        self.usage_tracker = UsageTracker(self.conn_factory)

        # Apply schema changes
        with self.conn_factory.with_conn() as conn:
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)

    @pytest.mark.asyncio
    async def test_increment_and_get_answer_count(self):
        """Test incrementing and getting answer count through UsageTracker."""
        bot_id = "tracker_test_bot"

        # Initially should be 0
        count = await self.usage_tracker.get_answer_count(bot_id)
        assert count == 0

        # Increment a few times
        await self.usage_tracker.increment_answer_count(bot_id)
        await self.usage_tracker.increment_answer_count(bot_id)
        await self.usage_tracker.increment_answer_count(bot_id)

        # Should now be 3
        count = await self.usage_tracker.get_answer_count(bot_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_usage_data_wrapper(self):
        """Test get_usage_data method through UsageTracker."""
        # Create some data
        await self.usage_tracker.increment_answer_count("bot_a")
        await self.usage_tracker.increment_answer_count("bot_a")
        await self.usage_tracker.increment_answer_count("bot_b")

        # Get all usage data
        data = await self.usage_tracker.get_usage_data(None)
        assert len(data) == 2

        # Get specific bot data
        bot_a_data = await self.usage_tracker.get_usage_data("bot_a")
        assert len(bot_a_data) == 1
        assert bot_a_data[0]["answer_count"] == 2

    @pytest.mark.asyncio
    async def test_multi_month_usage_tracking(self):
        """Test generating and retrieving usage data across multiple months."""
        # Test current month usage first
        bot_id = "multi_month_test_bot"

        # Add some usage for current month
        await self.usage_tracker.increment_answer_count(bot_id)
        await self.usage_tracker.increment_answer_count(bot_id)
        await self.usage_tracker.increment_answer_count(bot_id)

        # Get current month data
        current_count = await self.usage_tracker.get_answer_count(bot_id)
        assert current_count == 3

        # Get total count (should be same as current since it's the only month)
        total_count = await self.usage_tracker.get_total_answer_count(bot_id)
        assert total_count == 3

        # Simulate data for previous months using the testing helper method
        # This tests the retrieval functionality for multiple months
        await self.usage_tracker.insert_usage_data_for_testing(bot_id, 11, 2024, 5)  # November 2024
        await self.usage_tracker.insert_usage_data_for_testing(bot_id, 10, 2024, 8)  # October 2024

        # Get all usage data (should show multiple months)
        all_data = await self.usage_tracker.get_usage_data(bot_id)
        assert len(all_data) == 3  # Current month + 2 previous months

        # Verify data is sorted by year desc, month desc
        assert all_data[0]["year"] >= all_data[1]["year"]
        if all_data[0]["year"] == all_data[1]["year"]:
            assert all_data[0]["month"] >= all_data[1]["month"]

        # Get total count across all months
        total_count = await self.usage_tracker.get_total_answer_count(bot_id)
        assert total_count == 16  # 3 + 5 + 8

        # Get specific month counts
        nov_count = await self.usage_tracker.get_answer_count(bot_id, month=11, year=2024)
        assert nov_count == 5

        oct_count = await self.usage_tracker.get_answer_count(bot_id, month=10, year=2024)
        assert oct_count == 8

        # Get count for non-existent month
        sep_count = await self.usage_tracker.get_answer_count(bot_id, month=9, year=2024)
        assert sep_count == 0

        # Test with multiple bots across months
        bot2_id = "multi_month_bot2"

        # Add current month data for second bot
        await self.usage_tracker.increment_answer_count(bot2_id)

        # Add historical data for second bot
        await self.usage_tracker.insert_usage_data_for_testing(bot2_id, 11, 2024, 12)

        # Get all data for all bots
        all_bots_data = await self.usage_tracker.get_usage_data(None)

        # Should have data for both bots across multiple months
        bot_months = {}
        for record in all_bots_data:
            bot_id_key = record["bot_id"]
            if bot_id_key not in bot_months:
                bot_months[bot_id_key] = 0
            bot_months[bot_id_key] += 1

        assert bot_months[bot_id] == 3  # 3 months of data
        assert bot_months[bot2_id] == 2  # 2 months of data
