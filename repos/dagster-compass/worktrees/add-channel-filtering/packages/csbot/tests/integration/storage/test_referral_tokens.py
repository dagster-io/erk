"""Tests for referral token functionality in SlackbotStorage implementations."""

import asyncio
import os
import tempfile
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from csbot.slackbot.config import DatabaseConfig, UnsupportedKekConfig
from csbot.slackbot.storage.interface import ReferralTokenStatus
from csbot.slackbot.storage.sqlite import SlackbotSqliteStorage, SqliteConnectionFactory
from csbot.utils.time import SecondsNowFake

if TYPE_CHECKING:
    from testcontainers.postgres import PostgresContainer

    from csbot.slackbot.storage.postgresql import (
        PostgresqlConnectionFactory,
        SlackbotPostgresqlStorage,
    )

pytest_plugins = ("pytest_asyncio",)

# Try to import PostgreSQL components
try:
    from testcontainers.postgres import PostgresContainer

    from csbot.slackbot.storage.postgresql import (
        PostgresqlConnectionFactory,
        SlackbotPostgresqlStorage,
    )

    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False


class TestSqliteReferralTokens:
    """Test referral token functionality with SQLite storage."""

    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary SQLite database file for testing."""
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def time_fn(self):
        """Create a mock time provider."""
        return SecondsNowFake(1234567890)

    @pytest.fixture
    def sql_conn_factory(self, temp_db_file, time_fn):
        """Create SQLite connection factory for testing."""
        return SqliteConnectionFactory.from_db_config(
            DatabaseConfig.from_sqlite_path(temp_db_file), time_fn
        )

    @pytest.fixture
    def storage(self, sql_conn_factory, time_fn):
        """Create SQLite storage instance."""
        return SlackbotSqliteStorage(sql_conn_factory, time_fn)

    @pytest.fixture
    def setup_referral_tokens(self, storage):
        """Set up test referral tokens in the database."""
        # Insert test tokens directly into the database
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Create organizations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_name TEXT NOT NULL,
                    organization_industry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create bot_instances table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT NOT NULL,
                    bot_email TEXT NOT NULL,
                    organization_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE
                )
            """)

            # Create referral_tokens table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_tokens (
                    token TEXT PRIMARY KEY,
                    consumed_by_instance_id INTEGER,
                    consumed_at TIMESTAMP,
                    consumed_by_organization_ids TEXT DEFAULT '[]',
                    issued_by_organization_id INTEGER,
                    is_single_use INTEGER DEFAULT 1,
                    consumer_bonus_answers INTEGER DEFAULT 150
                )
            """)

            # Insert organization first
            cursor.execute(
                "INSERT INTO organizations (organization_name, organization_industry) VALUES (?, ?)",
                ("Test Organization", "Technology"),
            )
            org_id = cursor.lastrowid

            # Insert bot instances
            cursor.execute(
                "INSERT INTO bot_instances (id, channel_name, bot_email, organization_id) VALUES (?, ?, ?, ?)",
                (123, "test_channel_123", "test123@example.com", org_id),
            )
            cursor.execute(
                "INSERT INTO bot_instances (id, channel_name, bot_email, organization_id) VALUES (?, ?, ?, ?)",
                (456, "test_channel_456", "test456@example.com", org_id),
            )
            cursor.execute(
                "INSERT INTO bot_instances (id, channel_name, bot_email, organization_id) VALUES (?, ?, ?, ?)",
                (789, "test_channel_789", "test789@example.com", org_id),
            )
            cursor.execute(
                "INSERT INTO bot_instances (id, channel_name, bot_email, organization_id) VALUES (?, ?, ?, ?)",
                (999, "test_channel_999", "test999@example.com", org_id),
            )

            # Insert test tokens
            cursor.execute("INSERT INTO referral_tokens (token) VALUES (?)", ("valid_token",))
            cursor.execute(
                "INSERT INTO referral_tokens (token) VALUES (?)", ("another_valid_token",)
            )
            cursor.execute(
                """
                INSERT INTO referral_tokens (token, consumed_by_instance_id, consumed_at)
                VALUES (?, ?, datetime(?, 'unixepoch'))
            """,
                ("consumed_token", 123, 1234567800),
            )

            conn.commit()

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_valid_token(self, storage, setup_referral_tokens):
        """Test is_referral_token_valid with a valid unconsumed token."""
        result = await storage.is_referral_token_valid("valid_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is True
        assert result.has_been_consumed is False
        assert result.is_single_use is True

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_consumed_token(
        self, storage, setup_referral_tokens
    ):
        """Test is_referral_token_valid with a consumed token."""
        result = await storage.is_referral_token_valid("consumed_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_invalid_token(self, storage, setup_referral_tokens):
        """Test is_referral_token_valid with an invalid token."""
        result = await storage.is_referral_token_valid("invalid_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is False
        assert result.has_been_consumed is False
        assert result.is_single_use is False

    def test_mark_referral_token_consumed(self, storage, setup_referral_tokens, time_fn):
        """Test marking a referral token as consumed.

        Verifies that consumed_by_organization_ids is automatically populated.
        """
        import json

        # Mark token as consumed
        asyncio.run(storage.mark_referral_token_consumed("valid_token", 456))

        # Verify token is now consumed
        result = asyncio.run(storage.is_referral_token_valid("valid_token"))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

        # Verify database state
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            # Get the organization_id from bot_instances for comparison
            cursor.execute("SELECT organization_id FROM bot_instances WHERE id = ?", (456,))
            org_row = cursor.fetchone()
            expected_org_id = org_row[0] if org_row else None

            cursor.execute(
                """
                SELECT consumed_by_instance_id, consumed_at, consumed_by_organization_ids
                FROM referral_tokens
                WHERE token = ?
            """,
                ("valid_token",),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == 456
            assert row[1] is not None  # consumed_at should be set
            # consumed_by_organization_ids should contain the bot instance's org
            consumed_org_ids = json.loads(row[2]) if row[2] else []
            assert expected_org_id in consumed_org_ids

    def test_mark_referral_token_consumed_with_custom_timestamp(
        self, storage, setup_referral_tokens, time_fn
    ):
        """Test marking a referral token as consumed with custom timestamp."""
        custom_timestamp = 9876543210

        # Mark token as consumed with custom timestamp
        asyncio.run(
            storage.mark_referral_token_consumed("another_valid_token", 789, custom_timestamp)
        )

        # Verify token is consumed
        result = asyncio.run(storage.is_referral_token_valid("another_valid_token"))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

        # Verify database state with custom timestamp
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_instance_id, consumed_at FROM referral_tokens 
                WHERE token = ?
            """,
                ("another_valid_token",),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == 789
            # Convert back to timestamp to verify
            cursor.execute("SELECT strftime('%s', ?)", (row[1],))
            timestamp_result = cursor.fetchone()
            assert int(float(timestamp_result[0])) == custom_timestamp

    @pytest.mark.asyncio
    async def test_mark_nonexistent_token_consumed(self, storage, setup_referral_tokens):
        """Test marking a nonexistent token as consumed doesn't crash."""
        # This shouldn't raise an exception, just do nothing
        await storage.mark_referral_token_consumed("nonexistent_token", 999)

        # Token should still be invalid
        result = await storage.is_referral_token_valid("nonexistent_token")
        assert result.is_valid is False
        assert result.has_been_consumed is False
        assert result.is_single_use is False

    def test_mark_already_consumed_token(self, storage, setup_referral_tokens):
        """Test marking an already consumed token as consumed again."""
        # Mark already consumed token again with different instance ID
        asyncio.run(storage.mark_referral_token_consumed("consumed_token", 999))

        # Token should still be consumed
        result = asyncio.run(storage.is_referral_token_valid("consumed_token"))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

        # Verify the instance ID was updated
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_instance_id FROM referral_tokens 
                WHERE token = ?
            """,
                ("consumed_token",),
            )
            row = cursor.fetchone()
            assert row[0] == 999

    def test_referral_token_methods_use_time_provider(
        self, sql_conn_factory, setup_referral_tokens
    ):
        """Test that referral token methods use the provided time provider."""
        mock_time = SecondsNowFake(5555555555)
        storage = SlackbotSqliteStorage(sql_conn_factory, Mock(), mock_time)

        # Mark token as consumed (should use mock time provider)
        asyncio.run(storage.mark_referral_token_consumed("valid_token", 123))

        # Verify the timestamp matches our mock time
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_at FROM referral_tokens
                WHERE token = ?
            """,
                ("valid_token",),
            )
            row = cursor.fetchone()

            # Convert timestamp back to verify
            cursor.execute("SELECT strftime('%s', ?)", (row[0],))
            timestamp_result = cursor.fetchone()
            assert int(float(timestamp_result[0])) == 5555555555

    def test_create_token_with_parameters(self, storage):
        """Test creating tokens with various parameter combinations."""
        # Multi-use token with bonus
        token1 = "multi-use-with-bonus"
        storage.create_invite_token(token1, is_single_use=False, consumer_bonus_answers=150)

        # Single-use token with custom bonus
        token2 = "single-use-custom-bonus"
        storage.create_invite_token(token2, is_single_use=True, consumer_bonus_answers=500)

        # Multi-use token with zero bonus
        token3 = "multi-use-zero-bonus"
        storage.create_invite_token(token3, is_single_use=False, consumer_bonus_answers=0)

        # Verify all tokens were created correctly
        tokens = asyncio.run(storage.list_invite_tokens())
        token_dict = {t.token: t for t in tokens}

        assert token1 in token_dict
        assert token_dict[token1].is_single_use is False
        assert token_dict[token1].consumer_bonus_answers == 150

        assert token2 in token_dict
        assert token_dict[token2].is_single_use is True
        assert token_dict[token2].consumer_bonus_answers == 500

        assert token3 in token_dict
        assert token_dict[token3].is_single_use is False
        assert token_dict[token3].consumer_bonus_answers == 0

    def test_multi_use_token_consumed_by_multiple_orgs(self, storage, setup_referral_tokens):
        """Test that a multi-use token can be consumed by multiple organizations."""
        import json

        # Create two separate organizations for testing
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Create second organization
            cursor.execute(
                "INSERT INTO organizations (organization_name, organization_industry) VALUES (?, ?)",
                ("Second Organization", "Technology"),
            )
            org2_id = cursor.lastrowid

            # Create bot instance for second organization
            cursor.execute(
                "INSERT INTO bot_instances (id, channel_name, bot_email, organization_id) VALUES (?, ?, ?, ?)",
                (777, "test_channel_777", "test777@example.com", org2_id),
            )

            conn.commit()

        # Create a multi-use token
        token = "multi-use-token"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=150)

        # Consume by first organization (bot instance 456)
        asyncio.run(storage.mark_referral_token_consumed(token, 456))

        # Verify first consumption
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = ?",
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 1

            # Get the first org ID
            cursor.execute("SELECT organization_id FROM bot_instances WHERE id = ?", (456,))
            org1_id = cursor.fetchone()[0]
            assert org1_id in org_ids

        # Consume by second organization (bot instance 777, different org)
        asyncio.run(storage.mark_referral_token_consumed(token, 777))

        # Verify second consumption
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = ?",
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 2

            # Get the second org ID
            cursor.execute("SELECT organization_id FROM bot_instances WHERE id = ?", (777,))
            org2_id = cursor.fetchone()[0]
            assert org2_id in org_ids

        # Token should still be valid (multi-use)
        result = asyncio.run(storage.is_referral_token_valid(token))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is False

    def test_multi_use_token_same_org_multiple_times(self, storage, setup_referral_tokens):
        """Test that consuming a multi-use token with same org doesn't duplicate."""
        import json

        token = "multi-use-token-same-org"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=150)

        # Consume twice with same bot instance
        asyncio.run(storage.mark_referral_token_consumed(token, 456))
        asyncio.run(storage.mark_referral_token_consumed(token, 456))

        # Verify org ID only appears once
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = ?",
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 1


@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="PostgreSQL dependencies not available")
class TestPostgresqlReferralTokens:
    """Test referral token functionality with PostgreSQL storage."""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Session-scoped PostgreSQL container for testing."""
        # Use environment variable if available
        if test_db_url := os.environ.get("TEST_DATABASE_URL"):
            if test_db_url.startswith("postgresql://"):
                yield test_db_url
                return

        # Otherwise, spin up a test container
        with PostgresContainer(
            image="public.ecr.aws/docker/library/postgres:16-alpine3.21",
            username="test",
            password="test",
            dbname="test_db",
            driver="psycopg",
        ) as postgres:
            database_url = postgres.get_connection_url()
            os.environ["TEST_DATABASE_URL"] = database_url
            yield database_url

    @pytest.fixture
    def time_fn(self):
        """Create a mock time provider."""
        return SecondsNowFake(1234567890)

    @pytest.fixture
    def sql_conn_factory(self, postgres_container, time_fn):
        """Create PostgreSQL connection factory for testing."""
        return PostgresqlConnectionFactory.from_db_config(
            DatabaseConfig.from_uri(postgres_container), time_fn
        )

    @pytest.fixture
    def storage(self, sql_conn_factory, time_fn):
        """Create PostgreSQL storage instance."""
        return SlackbotPostgresqlStorage(sql_conn_factory, time_fn)

    @pytest.fixture
    def setup_referral_tokens(self, storage):
        """Set up test referral tokens in the database."""
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry)
                VALUES (%s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot instances to satisfy foreign key constraints
            cursor.execute(
                """
                INSERT INTO bot_instances (id, channel_name, bot_email, organization_id, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
            """,
                (123, "test_channel_123", "test123@example.com", org_id),
            )
            cursor.execute(
                """
                INSERT INTO bot_instances (id, channel_name, bot_email, organization_id, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
            """,
                (456, "test_channel_456", "test456@example.com", org_id),
            )
            cursor.execute(
                """
                INSERT INTO bot_instances (id, channel_name, bot_email, organization_id, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
            """,
                (789, "test_channel_789", "test789@example.com", org_id),
            )
            cursor.execute(
                """
                INSERT INTO bot_instances (id, channel_name, bot_email, organization_id, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
            """,
                (999, "test_channel_999", "test999@example.com", org_id),
            )

            # Clean up any existing test tokens first
            cursor.execute(
                "DELETE FROM referral_tokens WHERE token IN (%s, %s, %s)",
                ("valid_token", "another_valid_token", "consumed_token"),
            )

            # Insert test tokens (referral_tokens table should exist from schema)
            cursor.execute("INSERT INTO referral_tokens (token) VALUES (%s)", ("valid_token",))
            cursor.execute(
                "INSERT INTO referral_tokens (token) VALUES (%s)", ("another_valid_token",)
            )
            cursor.execute(
                """
                INSERT INTO referral_tokens (token, consumed_by_instance_id, consumed_at) 
                VALUES (%s, %s, to_timestamp(%s))
            """,
                ("consumed_token", 123, 1234567800),
            )

            conn.commit()

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_valid_token(self, storage, setup_referral_tokens):
        """Test is_referral_token_valid with a valid unconsumed token."""
        result = await storage.is_referral_token_valid("valid_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is True
        assert result.has_been_consumed is False
        assert result.is_single_use is True

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_consumed_token(
        self, storage, setup_referral_tokens
    ):
        """Test is_referral_token_valid with a consumed token."""
        result = await storage.is_referral_token_valid("consumed_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

    @pytest.mark.asyncio
    async def test_is_referral_token_valid_with_invalid_token(self, storage, setup_referral_tokens):
        """Test is_referral_token_valid with an invalid token."""
        result = await storage.is_referral_token_valid("invalid_token")

        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is False
        assert result.has_been_consumed is False
        assert result.is_single_use is False

    def test_mark_referral_token_consumed(self, storage, setup_referral_tokens, time_fn):
        """Test marking a referral token as consumed.

        Verifies that consumed_by_organization_ids is automatically populated from bot instance.
        """
        import json

        # Mark token as consumed
        asyncio.run(storage.mark_referral_token_consumed("valid_token", 456))

        # Verify token is now consumed
        result = asyncio.run(storage.is_referral_token_valid("valid_token"))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

        # Verify database state
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            # Get the organization_id from bot_instances for comparison
            cursor.execute(
                """
                SELECT organization_id FROM bot_instances WHERE id = %s
            """,
                (456,),
            )
            org_row = cursor.fetchone()
            expected_org_id = org_row[0] if org_row else None

            cursor.execute(
                """
                SELECT consumed_by_instance_id, consumed_at, consumed_by_organization_ids
                FROM referral_tokens
                WHERE token = %s
            """,
                ("valid_token",),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == 456
            assert row[1] is not None  # consumed_at should be set
            # consumed_by_organization_ids should contain the bot instance's org
            consumed_org_ids = json.loads(row[2]) if row[2] else []
            assert expected_org_id in consumed_org_ids

    def test_mark_referral_token_consumed_with_custom_timestamp(
        self, storage, setup_referral_tokens, time_fn
    ):
        """Test marking a referral token as consumed with custom timestamp."""
        custom_timestamp = 9876543210

        # Mark token as consumed with custom timestamp
        asyncio.run(
            storage.mark_referral_token_consumed("another_valid_token", 789, custom_timestamp)
        )

        # Verify token is consumed
        result = asyncio.run(storage.is_referral_token_valid("another_valid_token"))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is True

        # Verify database state with custom timestamp
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_instance_id, extract(epoch from consumed_at) FROM referral_tokens 
                WHERE token = %s
            """,
                ("another_valid_token",),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == 789
            assert int(float(row[1])) == custom_timestamp

    @pytest.mark.asyncio
    async def test_mark_nonexistent_token_consumed(self, storage, setup_referral_tokens):
        """Test marking a nonexistent token as consumed doesn't crash."""
        # This shouldn't raise an exception, just do nothing
        await storage.mark_referral_token_consumed("nonexistent_token", 999)

        # Token should still be invalid
        result = await storage.is_referral_token_valid("nonexistent_token")
        assert result.is_valid is False
        assert result.has_been_consumed is False
        assert result.is_single_use is False

    def test_referral_token_methods_use_time_provider(
        self, sql_conn_factory, setup_referral_tokens
    ):
        """Test that referral token methods use the provided time provider."""
        mock_time = SecondsNowFake(5555555555)
        storage = SlackbotPostgresqlStorage(sql_conn_factory, Mock(), mock_time)

        # Mark token as consumed (should use mock time provider)
        asyncio.run(storage.mark_referral_token_consumed("valid_token", 123))

        # Verify the timestamp matches our mock time
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT extract(epoch from consumed_at) FROM referral_tokens
                WHERE token = %s
            """,
                ("valid_token",),
            )
            row = cursor.fetchone()

            assert int(float(row[0])) == 5555555555

    def test_consumed_by_organization_ids_auto_population(self, storage, setup_referral_tokens):
        """Test that consumed_by_organization_ids is automatically populated.

        This test verifies the auto-population behavior by:
        1. Creating a referral token with issued_by_organization_id
        2. Consuming it with a bot instance
        3. Verifying consumed_by_organization_ids contains the bot's organization
        """
        import json

        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Get the organization_id for comparison
            cursor.execute(
                """
                SELECT organization_id FROM bot_instances WHERE id = %s
            """,
                (456,),
            )
            expected_org_id = cursor.fetchone()[0]

            # Create a new organization for issuing the token
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry)
                VALUES (%s, %s) RETURNING organization_id
            """,
                ("Issuing Org", "Technology"),
            )
            issuing_org_id = cursor.fetchone()[0]

            # Create a token with issued_by_organization_id
            cursor.execute(
                """
                INSERT INTO referral_tokens (token, issued_by_organization_id)
                VALUES (%s, %s)
            """,
                ("customer_referral_token", issuing_org_id),
            )
            conn.commit()

        # Mark token as consumed
        asyncio.run(storage.mark_referral_token_consumed("customer_referral_token", 456))

        # Verify both organization IDs are set correctly
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    issued_by_organization_id,
                    consumed_by_instance_id,
                    consumed_by_organization_ids
                FROM referral_tokens
                WHERE token = %s
            """,
                ("customer_referral_token",),
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == issuing_org_id, "issued_by_organization_id should be preserved"
            assert row[1] == 456, "consumed_by_instance_id should be set"
            # consumed_by_organization_ids should contain the bot instance's org
            consumed_org_ids = json.loads(row[2]) if row[2] else []
            assert expected_org_id in consumed_org_ids, (
                "consumed_by_organization_ids should contain the bot instance's organization"
            )

    def test_create_token_with_parameters(self, storage):
        """Test creating tokens with various parameter combinations."""
        # Multi-use token with bonus
        token1 = "multi-use-with-bonus"
        storage.create_invite_token(token1, is_single_use=False, consumer_bonus_answers=150)

        # Single-use token with custom bonus
        token2 = "single-use-custom-bonus"
        storage.create_invite_token(token2, is_single_use=True, consumer_bonus_answers=500)

        # Multi-use token with zero bonus
        token3 = "multi-use-zero-bonus"
        storage.create_invite_token(token3, is_single_use=False, consumer_bonus_answers=0)

        # Verify all tokens were created correctly
        tokens = asyncio.run(storage.list_invite_tokens())
        token_dict = {t.token: t for t in tokens}

        assert token1 in token_dict
        assert token_dict[token1].is_single_use is False
        assert token_dict[token1].consumer_bonus_answers == 150

        assert token2 in token_dict
        assert token_dict[token2].is_single_use is True
        assert token_dict[token2].consumer_bonus_answers == 500

        assert token3 in token_dict
        assert token_dict[token3].is_single_use is False
        assert token_dict[token3].consumer_bonus_answers == 0

    def test_multi_use_token_consumed_by_multiple_orgs(self, storage, setup_referral_tokens):
        """Test that a multi-use token can be consumed by multiple organizations."""
        import json

        # Create two separate organizations for testing
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Create second organization
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry)
                VALUES (%s, %s) RETURNING organization_id
            """,
                ("Second Organization", "Technology"),
            )
            org2_id = cursor.fetchone()[0]

            # Create bot instance for second organization
            cursor.execute(
                """
                INSERT INTO bot_instances (id, channel_name, bot_email, organization_id, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
            """,
                (777, "test_channel_777", "test777@example.com", org2_id),
            )

            conn.commit()

        # Create a multi-use token
        token = "multi-use-token"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=150)

        # Consume by first organization (bot instance 456)
        asyncio.run(storage.mark_referral_token_consumed(token, 456))

        # Verify first consumption
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = %s
            """,
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 1

            # Get the first org ID
            cursor.execute(
                """
                SELECT organization_id FROM bot_instances WHERE id = %s
            """,
                (456,),
            )
            org1_id = cursor.fetchone()[0]
            assert org1_id in org_ids

        # Consume by second organization (bot instance 777, different org)
        asyncio.run(storage.mark_referral_token_consumed(token, 777))

        # Verify second consumption
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = %s
            """,
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 2

            # Get the second org ID
            cursor.execute(
                """
                SELECT organization_id FROM bot_instances WHERE id = %s
            """,
                (777,),
            )
            org2_id = cursor.fetchone()[0]
            assert org2_id in org_ids

        # Token should still be valid (multi-use)
        result = asyncio.run(storage.is_referral_token_valid(token))
        assert result.is_valid is True
        assert result.has_been_consumed is True
        assert result.is_single_use is False

    def test_multi_use_token_same_org_multiple_times(self, storage, setup_referral_tokens):
        """Test that consuming a multi-use token with same org doesn't duplicate."""
        import json

        token = "multi-use-token-same-org"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=150)

        # Consume twice with same bot instance
        asyncio.run(storage.mark_referral_token_consumed(token, 456))
        asyncio.run(storage.mark_referral_token_consumed(token, 456))

        # Verify org ID only appears once
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = %s
            """,
                (token,),
            )
            row = cursor.fetchone()
            org_ids = json.loads(row[0])
            assert len(org_ids) == 1


class TestReferralTokenFactory:
    """Test referral token functionality through factory methods."""

    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary SQLite database file for testing."""
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_factory_created_storage_has_referral_token_methods(self, temp_db_file):
        """Test that storage created through factory has referral token methods."""
        from csbot.slackbot.storage.factory import create_storage_from_uri

        # Create storage through factory
        storage = await asyncio.to_thread(
            create_storage_from_uri, temp_db_file, UnsupportedKekConfig(), seed_database_from=None
        )

        # Verify it has the referral token methods
        assert hasattr(storage, "is_referral_token_valid")
        assert hasattr(storage, "mark_referral_token_consumed")
        assert hasattr(storage, "for_instance")

        # Test basic functionality
        result = await storage.is_referral_token_valid("nonexistent_token")
        assert isinstance(result, ReferralTokenStatus)
        assert result.is_valid is False
        assert result.has_been_consumed is False
        assert result.is_single_use is False

    def test_for_instance_method_creates_instance_storage(self, temp_db_file):
        """Test that for_instance method creates proper instance storage."""
        from csbot.slackbot.storage.factory import create_storage_from_uri

        # Create base storage through factory
        base_storage = create_storage_from_uri(
            temp_db_file, UnsupportedKekConfig(), seed_database_from=None
        )

        # Create instance storage
        instance_storage = base_storage.for_instance("test_bot")

        # Verify instance storage has both base and instance methods
        assert hasattr(instance_storage, "is_referral_token_valid")
        assert hasattr(instance_storage, "mark_referral_token_consumed")
        assert hasattr(instance_storage, "get")
        assert hasattr(instance_storage, "set")
        assert hasattr(instance_storage, "exists")
        assert hasattr(instance_storage, "delete")

        # Verify bot_id is set (cast to access bot_id attribute from instance storage)
        from csbot.slackbot.storage.sqlite import SlackbotInstanceSqliteStorage

        assert isinstance(instance_storage, SlackbotInstanceSqliteStorage)
        assert instance_storage.bot_id == "test_bot"


if __name__ == "__main__":
    pytest.main([__file__])
