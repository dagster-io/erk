"""
Test cases for SlackbotAnalyticsStore usage tracking.

Tests analytics store operations including usage tracking and organization methods.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slackbot_analytics import AnalyticsEventType, SlackbotAnalyticsStore
from csbot.slackbot.storage.schema_changes import SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory


class TestSlackbotAnalyticsStoreUsageTracking:
    """Test cases for usage tracking functionality in SlackbotAnalyticsStore."""

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
    async def test_increment_answer_count_new_bot(self):
        """Test incrementing answer count for a new bot."""
        bot_id = "test_bot_1"

        # Increment answer count
        await self.analytics_store.increment_answer_count(bot_id)

        # Verify count is 1
        data = await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )
        assert len(data) == 1
        assert data[0]["bot_id"] == bot_id
        assert data[0]["answer_count"] == 1

    @pytest.mark.asyncio
    async def test_increment_answer_count_existing_bot(self):
        """Test incrementing answer count for an existing bot."""
        bot_id = "test_bot_2"

        # Increment multiple times
        await self.analytics_store.increment_answer_count(bot_id)
        await self.analytics_store.increment_answer_count(bot_id)
        await self.analytics_store.increment_answer_count(bot_id)

        # Verify count is 3
        data = await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )
        assert len(data) == 1
        assert data[0]["answer_count"] == 3

    @pytest.mark.asyncio
    async def test_get_usage_tracking_data_all_bots(self):
        """Test getting usage tracking data for all bots."""
        # Create data for multiple bots
        await self.analytics_store.increment_answer_count("bot_1")
        await self.analytics_store.increment_answer_count("bot_1")
        await self.analytics_store.increment_answer_count("bot_2")
        await self.analytics_store.increment_answer_count("bot_3")
        await self.analytics_store.increment_answer_count("bot_3")
        await self.analytics_store.increment_answer_count("bot_3")

        # Get all data
        data = await self.analytics_store.get_usage_tracking_data(None, include_bonus_answers=True)

        # Should have 3 bots
        assert len(data) == 3

        # Create lookup by bot_id
        bot_counts = {item["bot_id"]: item["answer_count"] for item in data}

        assert bot_counts["bot_1"] == 2
        assert bot_counts["bot_2"] == 1
        assert bot_counts["bot_3"] == 3

    @pytest.mark.asyncio
    async def test_get_usage_tracking_data_specific_bot(self):
        """Test getting usage tracking data for a specific bot."""
        # Create data for multiple bots
        await self.analytics_store.increment_answer_count("bot_target")
        await self.analytics_store.increment_answer_count("bot_target")
        await self.analytics_store.increment_answer_count("bot_other")

        # Get data for specific bot
        data = await self.analytics_store.get_usage_tracking_data(
            "bot_target", include_bonus_answers=True
        )

        # Should have only 1 bot
        assert len(data) == 1
        assert data[0]["bot_id"] == "bot_target"
        assert data[0]["answer_count"] == 2

    @pytest.mark.asyncio
    async def test_get_usage_tracking_data_nonexistent_bot(self):
        """Test getting usage tracking data for a nonexistent bot."""
        # Get data for nonexistent bot
        data = await self.analytics_store.get_usage_tracking_data(
            "nonexistent_bot", include_bonus_answers=True
        )

        # Should be empty
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_increment_answer_count_concurrent_access(self):
        """Test concurrent increments to the same bot."""
        import asyncio

        bot_id = "concurrent_bot"

        # Create multiple concurrent increment tasks
        tasks = [self.analytics_store.increment_answer_count(bot_id) for _ in range(10)]

        # Execute all tasks concurrently
        await asyncio.gather(*tasks)

        # Verify final count is 10
        data = await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )
        assert len(data) == 1
        assert data[0]["answer_count"] == 10

    @pytest.mark.asyncio
    async def test_usage_tracking_with_analytics_disabled(self):
        """Test usage tracking when analytics is disabled."""
        # Create a mock connection factory that doesn't support analytics
        mock_conn_factory = Mock()
        mock_conn_factory.supports_analytics.return_value = False

        analytics_store = SlackbotAnalyticsStore(mock_conn_factory)

        # Operations should succeed but do nothing
        await analytics_store.increment_answer_count("test_bot")
        data = await analytics_store.get_usage_tracking_data("test_bot", include_bonus_answers=True)

        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_usage_tracking_data_for_month(self):
        """Test getting usage tracking data for a specific month."""
        bot_id = "test_bot_monthly"

        # Add usage data for current month
        await self.analytics_store.increment_answer_count(bot_id)
        await self.analytics_store.increment_answer_count(bot_id)
        await self.analytics_store.increment_answer_count(bot_id)

        # Get current month and year
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year

        # Test getting usage for current month
        current_usage = await self.analytics_store.get_usage_tracking_data_for_month(
            bot_id, current_month, current_year, include_bonus_answers=True
        )
        assert current_usage == 3

        # Test getting usage for non-existent month
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_usage = await self.analytics_store.get_usage_tracking_data_for_month(
            bot_id, prev_month, prev_year, include_bonus_answers=True
        )
        assert prev_usage == 0

        # Add historical data manually for testing
        await self.analytics_store.insert_usage_tracking_data(bot_id, prev_month, prev_year, 5)

        # Test getting historical usage
        historical_usage = await self.analytics_store.get_usage_tracking_data_for_month(
            bot_id, prev_month, prev_year, include_bonus_answers=True
        )
        assert historical_usage == 5

        # Test with nonexistent bot
        nonexistent_usage = await self.analytics_store.get_usage_tracking_data_for_month(
            "nonexistent_bot", current_month, current_year, include_bonus_answers=True
        )
        assert nonexistent_usage == 0


class TestSlackbotAnalyticsStoreOrganizationMethods:
    """Test cases for organization-based analytics methods in SlackbotAnalyticsStore."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.conn_factory = SqliteConnectionFactory.temporary_for_testing()
        self.analytics_store = SlackbotAnalyticsStore(self.conn_factory)

        # Apply schema changes
        with self.conn_factory.with_conn() as conn:
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)

            # Set up test organization and bot instances
            cursor = conn.cursor()

            # Create test organizations first
            cursor.execute("""
                INSERT INTO organizations (organization_id, organization_name, organization_industry)
                VALUES
                    (123, 'Test Org 123', 'Technology'),
                    (456, 'Test Org 456', 'Finance')
            """)

            # Create test organization with multiple bot instances
            org_id = 123
            cursor.execute(
                """
                INSERT INTO bot_instances (slack_team_id, channel_name, organization_id, bot_email)
                VALUES
                    ('T123', 'channel1', ?, 'bot1@example.com'),
                    ('T123', 'channel2', ?, 'bot2@example.com'),
                    ('T456', 'channel3', ?, 'bot3@example.com')
            """,
                (org_id, org_id, org_id),
            )

            # Create different organization for testing isolation
            other_org_id = 456
            cursor.execute(
                """
                INSERT INTO bot_instances (slack_team_id, channel_name, organization_id, bot_email)
                VALUES ('T789', 'other-channel', ?, 'bot4@example.com')
            """,
                (other_org_id,),
            )

            conn.commit()

    @pytest.mark.asyncio
    async def test_get_organization_usage_tracking_data_aggregates_across_bots(self):
        """Test that organization usage data aggregates across all bots in organization."""
        org_id = 123

        # Create usage data for bots in the organization
        bot1_id = BotKey.from_channel_name("T123", "channel1").to_bot_id()
        bot2_id = BotKey.from_channel_name("T123", "channel2").to_bot_id()
        bot3_id = BotKey.from_channel_name("T456", "channel3").to_bot_id()

        # Add usage for bots in organization 123
        await self.analytics_store.increment_answer_count(bot1_id)  # 1 answer
        await self.analytics_store.increment_answer_count(bot1_id)  # 2 answers total
        await self.analytics_store.increment_answer_count(bot2_id)  # 1 answer
        await self.analytics_store.increment_answer_count(bot3_id)  # 1 answer

        # Add usage for bot in different organization (should not be included)
        other_bot_id = BotKey.from_channel_name("T789", "other-channel").to_bot_id()
        await self.analytics_store.increment_answer_count(other_bot_id)  # Should not be included

        # Get organization usage data
        data = await self.analytics_store.get_organization_usage_tracking_data(
            org_id, include_bonus_answers=False
        )

        # Should have 3 entries (one for each bot in the organization)
        assert len(data) == 3

        # Verify we got data for the right bots
        bot_ids_in_data = {item["bot_id"] for item in data}
        assert bot_ids_in_data == {bot1_id, bot2_id, bot3_id}

        # Verify answer counts
        bot_counts = {item["bot_id"]: item["answer_count"] for item in data}
        assert bot_counts[bot1_id] == 2
        assert bot_counts[bot2_id] == 1
        assert bot_counts[bot3_id] == 1

        # Verify other org bot is not included
        assert other_bot_id not in bot_ids_in_data

    @pytest.mark.asyncio
    async def test_get_organization_analytics_data_filters_by_organization(self):
        """Test that organization analytics data only includes bots from that organization."""
        org_id = 123

        # Create analytics events for bots in the organization
        bot1_id = BotKey.from_channel_name("T123", "channel1").to_bot_id()
        bot2_id = BotKey.from_channel_name("T123", "channel2").to_bot_id()
        other_bot_id = BotKey.from_channel_name("T789", "other-channel").to_bot_id()

        # Add analytics events
        await self.analytics_store.log_analytics_event(
            bot1_id,
            AnalyticsEventType.NEW_CONVERSATION,
            organization_name="org",
            channel_id="C123",
            user_id="U001",
        )
        await self.analytics_store.log_analytics_event(
            bot2_id,
            AnalyticsEventType.NEW_REPLY,
            organization_name="org",
            channel_id="C124",
            user_id="U002",
        )
        await self.analytics_store.log_analytics_event(
            other_bot_id,
            AnalyticsEventType.NEW_CONVERSATION,
            organization_name="org",
            channel_id="C999",
            user_id="U999",
        )

        # Get organization analytics data
        data = await self.analytics_store.get_organization_analytics_data(org_id)

        # Should have 2 events (from bots in organization 123)
        assert len(data) == 2

        # Verify we got events for the right bots
        bot_ids_in_data = {item["bot_id"] for item in data}
        assert bot_ids_in_data == {bot1_id, bot2_id}

        # Verify event details
        events_by_bot = {item["bot_id"]: item for item in data}
        assert events_by_bot[bot1_id]["event_type"] == "new_conversation"
        assert events_by_bot[bot1_id]["user_id"] == "U001"
        assert events_by_bot[bot2_id]["event_type"] == "new_reply"
        assert events_by_bot[bot2_id]["user_id"] == "U002"

        # Verify other org event is not included
        assert other_bot_id not in bot_ids_in_data

    @pytest.mark.asyncio
    async def test_get_organization_usage_tracking_data_empty_organization(self):
        """Test organization usage data for organization with no bots."""
        empty_org_id = 999

        # Get data for organization with no bots
        data = await self.analytics_store.get_organization_usage_tracking_data(
            empty_org_id, include_bonus_answers=False
        )

        # Should be empty
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_organization_usage_tracking_data_with_bonus_answers(self):
        """Test organization usage data with bonus answers included."""
        org_id = 123

        # Create usage with bonus answers
        bot1_id = BotKey.from_channel_name("T123", "channel1").to_bot_id()

        # Add regular and bonus answers
        await self.analytics_store.increment_answer_count(bot1_id)  # Regular answer
        await self.analytics_store.increment_bonus_answer_count(bot1_id)  # Bonus answer

        # Get data without bonus answers
        data_no_bonus = await self.analytics_store.get_organization_usage_tracking_data(
            org_id, include_bonus_answers=False
        )

        # Get data with bonus answers
        data_with_bonus = await self.analytics_store.get_organization_usage_tracking_data(
            org_id, include_bonus_answers=True
        )

        # Verify counts
        assert len(data_no_bonus) == 1
        assert len(data_with_bonus) == 1
        assert data_no_bonus[0]["answer_count"] == 1  # Only regular
        assert data_with_bonus[0]["answer_count"] == 2  # Regular + bonus
