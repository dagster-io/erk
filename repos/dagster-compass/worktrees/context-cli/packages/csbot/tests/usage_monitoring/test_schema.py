"""
Test cases for usage tracking table schema.

Tests schema creation, migration, and validation for usage tracking tables.
"""

import pytest

from csbot.slackbot.storage.schema_changes import CreateUsageTrackingTable, SchemaManager
from csbot.slackbot.storage.sqlite import SqliteConnectionFactory


class TestUsageTrackingTableSchema:
    """Test cases for usage tracking table schema creation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.conn_factory = SqliteConnectionFactory.temporary_for_testing()

    def test_usage_tracking_table_creation(self):
        """Test that usage tracking table is created with correct schema."""
        with self.conn_factory.with_conn() as conn:
            # Apply full schema manager to get final table structure
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)

            # Verify table exists
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='usage_tracking'"
            )
            result = cursor.fetchone()
            assert result is not None

            # Verify table structure (after monthly migration)
            cursor.execute("PRAGMA table_info(usage_tracking)")
            columns = cursor.fetchall()

            column_names = [col[1] for col in columns]
            expected_columns = [
                "id",
                "bot_id",
                "month",
                "year",
                "answer_count",
                "created_at",
                "updated_at",
            ]

            for col in expected_columns:
                assert col in column_names

            # Verify indexes exist (after migration)
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='usage_tracking'"
            )
            indexes = cursor.fetchall()
            index_names = [idx[0] for idx in indexes]

            assert "idx_usage_tracking_bot_id_month_year" in index_names
            assert "idx_usage_tracking_year_month" in index_names

    def test_schema_manager_includes_usage_tracking(self):
        """Test that schema manager includes usage tracking table creation."""
        schema_manager = SchemaManager()

        # Check that CreateUsageTrackingTable is in the base changes
        usage_tracking_changes = [
            change
            for change in schema_manager.base_changes
            if isinstance(change, CreateUsageTrackingTable)
        ]

        assert len(usage_tracking_changes) == 1

    def test_usage_tracking_table_unique_constraint(self):
        """Test that bot_id, month, year combination has unique constraint."""
        with self.conn_factory.with_conn() as conn:
            # Apply full schema manager to get monthly schema
            schema_manager = SchemaManager()
            schema_manager.apply_all_changes(conn)

            cursor = conn.cursor()

            # Insert first record for current month
            cursor.execute("""
                INSERT INTO usage_tracking (bot_id, month, year, answer_count)
                VALUES ('test_bot', 8, 2025, 1)
            """)

            # Attempt to insert duplicate bot_id, month, year should fail
            with pytest.raises(Exception):  # SQLite raises IntegrityError
                cursor.execute("""
                    INSERT INTO usage_tracking (bot_id, month, year, answer_count)
                    VALUES ('test_bot', 8, 2025, 2)
                """)
