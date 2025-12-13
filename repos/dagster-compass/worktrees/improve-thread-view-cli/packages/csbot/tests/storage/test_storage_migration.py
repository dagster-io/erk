"""Tests for database schema migration scenarios."""

import asyncio
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from csbot.slackbot.storage.sqlite import SlackbotInstanceSqliteStorage, SqliteConnectionFactory
from csbot.utils.time import SecondsNowFake


class TestSlackbotStorageMigration:
    """Test suite for database schema migration scenarios."""

    @pytest.fixture
    def time_provider(self):
        """Create a controllable time provider starting at timestamp 1000."""
        return SecondsNowFake(1000)

    def test_migration_from_old_schema_without_deleted_at_column(self, time_provider):
        """Test migration from old schema that doesn't have deleted_at_seconds column."""
        # Create an in-memory database connection manually
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        try:
            # Create the OLD schema (without deleted_at_seconds column)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE kv (
                    bot_id TEXT,
                    family TEXT,
                    key TEXT,
                    value TEXT,
                    expires_at_seconds INTEGER,
                    PRIMARY KEY (bot_id, family, key)
                )
            """)
            cursor.execute("CREATE INDEX idx_kv_expires_at_seconds ON kv (expires_at_seconds)")

            # Insert some test data using the old schema
            test_data = [
                ("bot1", "family1", "key1", "value1", -1),  # No expiry
                ("bot1", "family1", "key2", "value2", 2000),  # Expires at 2000
                ("bot1", "family2", "key1", "value3", -1),  # No expiry, different family
                ("bot2", "family1", "key1", "value4", 1500),  # Different bot, expires at 1500
            ]

            cursor.executemany(
                (
                    "INSERT INTO kv (bot_id, family, key, value, expires_at_seconds) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                test_data,
            )
            conn.commit()

            # Verify data was inserted
            cursor.execute("SELECT COUNT(*) FROM kv")
            assert cursor.fetchone()[0] == 4

            # Now create a connection factory that uses this existing connection
            # This simulates the scenario where we're connecting to an existing database
            def connection_context():
                from contextlib import contextmanager

                @contextmanager
                def ctx():
                    conn = sqlite3.connect(path)
                    yield conn

                return ctx()

            factory = SqliteConnectionFactory(connection_context, time_provider)

            # When we initialize the database, it should add the new column with defaults
            # We need to explicitly call _initialize_database since we created the factory directly
            with factory.with_conn() as conn:
                factory._initialize_database(conn)

            # Verify the new column was added
            cursor.execute("PRAGMA table_info(kv)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            assert "deleted_at_seconds" in column_names

            # Verify that existing data has the correct default value (-1 = not deleted)
            cursor.execute(
                "SELECT bot_id, family, key, deleted_at_seconds FROM kv "
                "ORDER BY bot_id, family, key"
            )
            rows = cursor.fetchall()

            expected_rows = [
                ("bot1", "family1", "key1", -1),
                ("bot1", "family1", "key2", -1),
                ("bot1", "family2", "key1", -1),
                ("bot2", "family1", "key1", -1),
            ]

            assert rows == expected_rows

            # Now test that the storage system works correctly with the migrated data
            storage = SlackbotInstanceSqliteStorage(factory, "bot1", Mock(), time_provider)

            # Should be able to read existing data
            assert asyncio.run(storage.get("family1", "key1")) == "value1"
            assert asyncio.run(storage.get("family1", "key2")) == "value2"  # Not expired yet
            assert asyncio.run(storage.get("family2", "key1")) == "value3"
            assert asyncio.run(storage.exists("family1", "key1")) is True
            assert asyncio.run(storage.exists("family1", "key2")) is True
            assert asyncio.run(storage.exists("family2", "key1")) is True

            # Test bot isolation still works
            storage_bot2 = SlackbotInstanceSqliteStorage(factory, "bot2", Mock(), time_provider)
            assert asyncio.run(storage_bot2.get("family1", "key1")) == "value4"
            assert (
                asyncio.run(storage.get("family1", "key1")) == "value1"
            )  # Different value for bot1

            # Test expiry with migrated data
            time_provider.advance_time(600)  # Advance to time 1600

            # key2 should be expired now (expires_at_seconds = 2000, current = 1600,
            # so not expired yet)
            assert asyncio.run(storage.get("family1", "key2")) == "value2"

            # Advance past expiry
            time_provider.advance_time(500)  # Now at time 2100
            assert asyncio.run(storage.get("family1", "key2")) is None  # Should be expired
            assert asyncio.run(storage.exists("family1", "key2")) is False

            # Test that new entries work correctly
            asyncio.run(storage.set("family1", "new_key", "new_value", expiry_seconds=100))
            assert asyncio.run(storage.get("family1", "new_key")) == "new_value"

            # Test soft delete works
            asyncio.run(storage.delete("family1", "key1"))
            assert asyncio.run(storage.get("family1", "key1")) is None
            assert asyncio.run(storage.exists("family1", "key1")) is False

            # Verify it was soft deleted (deleted_at_seconds should not be -1)
            cursor.execute(
                "SELECT deleted_at_seconds FROM kv WHERE bot_id = ? AND family = ? AND key = ?",
                ("bot1", "family1", "key1"),
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] != -1  # Should be soft deleted with timestamp

        finally:
            conn.close()

    def test_migration_preserves_analytics_table(self, time_provider):
        """Test that migration doesn't affect the analytics table."""
        # Create an in-memory database connection manually
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        try:
            # Create the OLD schema with analytics table
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE kv (
                    bot_id TEXT,
                    family TEXT,
                    key TEXT,
                    value TEXT,
                    expires_at_seconds INTEGER,
                    PRIMARY KEY (bot_id, family, key)
                )
            """)
            cursor.execute("""
                CREATE TABLE analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert some analytics data
            cursor.execute(
                "INSERT INTO analytics (bot_id, event_type) VALUES (?, ?)",
                ("test_bot", "test_event"),
            )
            conn.commit()

            # Verify analytics data exists
            cursor.execute("SELECT COUNT(*) FROM analytics")
            assert cursor.fetchone()[0] == 1

            # Create connection factory and initialize (this runs migration)
            def connection_context():
                from contextlib import contextmanager

                @contextmanager
                def ctx():
                    conn = sqlite3.connect(path)
                    yield conn

                return ctx()

            factory = SqliteConnectionFactory(connection_context, time_provider)
            with factory.with_conn() as conn:
                factory._initialize_database(conn)  # Migration happens here

            # Verify analytics data is still there
            cursor.execute("SELECT bot_id, event_type FROM analytics")
            row = cursor.fetchone()
            assert row == ("test_bot", "test_event")

            # Verify kv table was migrated
            cursor.execute("PRAGMA table_info(kv)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            assert "deleted_at_seconds" in column_names

        finally:
            conn.close()

    def test_migration_idempotency(self, time_provider):
        """Test that migrations can be applied multiple times without issues."""
        # Create an in-memory database connection manually
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        try:
            # Create the OLD schema (without deleted_at_seconds column)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE kv (
                    bot_id TEXT,
                    family TEXT,
                    key TEXT,
                    value TEXT,
                    expires_at_seconds INTEGER,
                    PRIMARY KEY (bot_id, family, key)
                )
            """)
            cursor.execute("CREATE INDEX idx_kv_expires_at_seconds ON kv (expires_at_seconds)")

            # Insert some test data
            cursor.execute(
                "INSERT INTO kv (bot_id, family, key, value, expires_at_seconds) "
                "VALUES (?, ?, ?, ?, ?)",
                ("bot1", "family1", "key1", "value1", -1),
            )
            conn.commit()

            # Create connection factory that uses this database
            def connection_context():
                from contextlib import contextmanager

                @contextmanager
                def ctx():
                    conn = sqlite3.connect(path)
                    yield conn

                return ctx()

            factory = SqliteConnectionFactory(connection_context, time_provider)

            # Apply migrations first time
            with factory.with_conn() as conn:
                factory._initialize_database(conn)

            # Verify migration was applied
            cursor.execute("PRAGMA table_info(kv)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            assert "deleted_at_seconds" in column_names

            # Verify data is intact
            cursor.execute(
                "SELECT value FROM kv WHERE bot_id = ? AND family = ? AND key = ?",
                ("bot1", "family1", "key1"),
            )
            assert cursor.fetchone()[0] == "value1"

            # Apply migrations SECOND time - this should be safe and idempotent
            with factory.with_conn() as conn:
                factory._initialize_database(conn)

            # Verify schema is still correct
            cursor.execute("PRAGMA table_info(kv)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            assert "deleted_at_seconds" in column_names

            # Verify data is still intact
            cursor.execute(
                "SELECT value FROM kv WHERE bot_id = ? AND family = ? AND key = ?",
                ("bot1", "family1", "key1"),
            )
            assert cursor.fetchone()[0] == "value1"

            # Apply migrations THIRD time to be extra sure
            with factory.with_conn() as conn:
                factory._initialize_database(conn)

            # Verify everything still works by using the storage system
            storage = SlackbotInstanceSqliteStorage(factory, "bot1", time_provider)
            assert asyncio.run(storage.get("family1", "key1")) == "value1"

            # Test that we can still perform operations
            asyncio.run(storage.set("family1", "new_key", "new_value"))
            assert asyncio.run(storage.get("family1", "new_key")) == "new_value"

            asyncio.run(storage.delete("family1", "key1"))
            assert asyncio.run(storage.get("family1", "key1")) is None

        finally:
            conn.close()

    def test_fresh_database_has_correct_schema(self, time_provider):
        """Test that a fresh database gets the correct schema from the start."""
        factory = SqliteConnectionFactory.temporary_for_testing(time_provider)

        # Create storage to trigger initialization
        storage = SlackbotInstanceSqliteStorage(factory, "test_bot", time_provider)

        # Check that all expected columns exist
        with factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(kv)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            expected_columns = [
                "bot_id",
                "family",
                "key",
                "value",
                "expires_at_seconds",
                "deleted_at_seconds",
            ]

            for col in expected_columns:
                assert col in column_names, f"Missing column: {col}"

            # Check that deleted_at_seconds has correct default
            deleted_at_col = next(col for col in columns if col[1] == "deleted_at_seconds")
            assert deleted_at_col[4] == "-1", "deleted_at_seconds should default to -1"

        # Test basic functionality
        asyncio.run(storage.set("family", "key", "value"))
        assert asyncio.run(storage.get("family", "key")) == "value"
        assert asyncio.run(storage.exists("family", "key")) is True

        asyncio.run(storage.delete("family", "key"))
        assert asyncio.run(storage.get("family", "key")) is None
        assert asyncio.run(storage.exists("family", "key")) is False
