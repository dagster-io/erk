"""
Test cases for CLI export functionality.

Tests CSV export and command-line interface for usage tracking data.
"""

import csv
import tempfile
from pathlib import Path

import pytest

from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.schema_changes import SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory


class TestUsageTrackingCLI:
    """Test cases for CLI export functionality."""

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
    async def test_export_usage_tracking_to_csv(self):
        """Test exporting usage tracking data to CSV."""
        # Create some test data
        await self.analytics_store.increment_answer_count("bot_1")
        await self.analytics_store.increment_answer_count("bot_1")
        await self.analytics_store.increment_answer_count("bot_2")
        await self.analytics_store.increment_answer_count("bot_3")
        await self.analytics_store.increment_answer_count("bot_3")
        await self.analytics_store.increment_answer_count("bot_3")

        # Get the data
        data = await self.analytics_store.get_usage_tracking_data(None, include_bonus_answers=True)

        # Export to temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_file:
            csv_path = tmp_file.name

            fieldnames = ["bot_id", "month", "year", "answer_count", "created_at", "updated_at"]
            writer = csv.DictWriter(tmp_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        # Read back and verify
        with open(csv_path) as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        # Clean up
        Path(csv_path).unlink()

        # Verify CSV contents
        assert len(rows) == 3

        # Create lookup by bot_id
        csv_bot_counts = {row["bot_id"]: int(row["answer_count"]) for row in rows}

        assert csv_bot_counts["bot_1"] == 2
        assert csv_bot_counts["bot_2"] == 1
        assert csv_bot_counts["bot_3"] == 3

        # Verify all expected fields are present
        for row in rows:
            assert "bot_id" in row
            assert "month" in row
            assert "year" in row
            assert "answer_count" in row
            assert "created_at" in row
            assert "updated_at" in row
