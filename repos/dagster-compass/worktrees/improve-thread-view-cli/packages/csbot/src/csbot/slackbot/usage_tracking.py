"""
Usage tracking for pricing model.

This module provides functionality to track the number of answers (invocations
of streaming_reply_to_thread_with_ai) per bot for pricing purposes.

The usage tracking table stores a simple count of answers per bot_id,
which is what's needed for the pricing model.
"""

from typing import Any

import pytz

from .slackbot_analytics import SlackbotAnalyticsStore
from .storage.interface import SqlConnectionFactory


class UsageTracker:
    """Tracks usage metrics for pricing model."""

    def __init__(self, sql_conn_factory: SqlConnectionFactory):
        self.analytics_store = SlackbotAnalyticsStore(sql_conn_factory)

    async def increment_answer_count(self, bot_id: str) -> None:
        """Increment the answer count for a bot.

        This should be called once for each invocation of streaming_reply_to_thread_with_ai
        to track answers for pricing purposes.

        Args:
            bot_id: The bot ID to increment the count for
        """
        await self.analytics_store.increment_answer_count(bot_id)

    async def get_usage_data(self, bot_id: str | None) -> list[dict[str, Any]]:
        """Get usage tracking data.

        Args:
            bot_id: Optional bot ID to filter by. If None, returns data for all bots.

        Returns:
            List of dictionaries with usage tracking data
        """
        return await self.analytics_store.get_usage_tracking_data(
            bot_id, include_bonus_answers=True
        )

    async def get_answer_count(
        self, bot_id: str, month: int | None = None, year: int | None = None
    ) -> int:
        """Get the answer count for a bot, optionally for a specific month/year.

        Args:
            bot_id: The bot ID to get the count for
            month: Optional month (1-12). If None, gets total for current month
            year: Optional year. If None, gets total for current year

        Returns:
            The answer count for the bot in the specified period, or 0 if no data exists
        """
        from datetime import datetime

        data = await self.get_usage_data(bot_id)
        if not data:
            return 0

        # If no month/year specified, use current month/year
        if month is None:
            month = datetime.now(pytz.utc).month
        if year is None:
            year = datetime.now(pytz.utc).year

        # Filter data for the specific month/year
        for entry in data:
            if entry["month"] == month and entry["year"] == year:
                return entry["answer_count"]

        return 0

    async def get_total_answer_count(self, bot_id: str) -> int:
        """Get the total answer count across all months for a bot.

        Args:
            bot_id: The bot ID to get the count for

        Returns:
            The total answer count for the bot across all months, or 0 if no data exists
        """
        data = await self.get_usage_data(bot_id)
        if not data:
            return 0

        return sum(entry["answer_count"] for entry in data)

    async def insert_usage_data_for_testing(
        self, bot_id: str, month: int, year: int, answer_count: int
    ) -> None:
        """Insert usage tracking data for a specific month/year (for testing purposes only).

        Args:
            bot_id: The bot ID to insert data for
            month: Month (1-12)
            year: Year (e.g., 2024)
            answer_count: Number of answers for this month
        """
        await self.analytics_store.insert_usage_tracking_data(bot_id, month, year, answer_count)
