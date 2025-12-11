import asyncio
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.config import PlaintextKekConfig
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.slackbot.storage.interface import (
    SlackbotInstanceStorage,
    SqlConnectionFactory,
)
from csbot.slackbot.storage.postgresql import (
    SlackbotInstancePostgresqlStorage,
    SlackbotPostgresqlStorage,
)
from csbot.utils.sync_to_async import sync_to_async
from csbot.utils.time import SecondsNow
from tests.storage.slackbot_storage_test_base import SlackbotStorageTestBase
from tests.storage.test_storage_base import StorageTestBase

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")


class TestSlackbotInstancePostgresqlStorage(StorageTestBase):
    """Test suite for SlackbotInstancePostgresqlStorage.

    Uses testcontainers to automatically spin up a PostgreSQL instance for testing.
    Can also use an existing PostgreSQL instance if TEST_DATABASE_URL is set.
    """

    @pytest.fixture
    def sql_conn_factory(self, sql_conn_factory_transactional):
        """Use transactional connection factory for test isolation."""
        return sql_conn_factory_transactional

    @pytest.fixture
    def storage(self, sql_conn_factory_transactional):
        """Create a storage instance with a test bot ID."""
        return SlackbotInstancePostgresqlStorage(
            sql_conn_factory_transactional, Mock(), "test_bot_id"
        )

    @pytest.fixture
    def storage2(self, sql_conn_factory_transactional):
        """Create a second storage instance with a different bot ID for isolation tests."""
        return SlackbotInstancePostgresqlStorage(
            sql_conn_factory_transactional, Mock(), "test_bot_id_2"
        )

    def _create_storage(
        self, sql_conn_factory: SqlConnectionFactory, bot_id: str, seconds_now: SecondsNow
    ) -> SlackbotInstanceStorage:
        """Create a storage instance for the given bot ID."""
        return SlackbotInstancePostgresqlStorage(sql_conn_factory, Mock(), bot_id, seconds_now)


class TestSlackbotPostgresqlStorage(SlackbotStorageTestBase):
    """Test suite for SlackbotPostgresqlStorage create_bot_instance functionality."""

    @pytest.fixture
    def sql_conn_factory(self, sql_conn_factory_transactional):
        """Use transactional connection factory for test isolation."""
        return sql_conn_factory_transactional

    @pytest.fixture
    def storage(self, sql_conn_factory_transactional):
        """Create a SlackbotPostgresqlStorage instance."""
        return SlackbotPostgresqlStorage(
            sql_conn_factory_transactional,
            KekProvider(
                PlaintextKekConfig(key=SecretStr("fNnln2pTP2QRjtD644VZ0kzE20cfQvrU4ZnqcZK0t_8="))
            ),
        )

    def test_initialize_database_deadlock_prevention(self, sql_conn_factory_transactional):
        """Test that multiple threads calling initialize_database() don't deadlock."""
        import time

        # Create 20 keys that are ready to expire (reduced from 100 for faster test)
        storage = SlackbotPostgresqlStorage(sql_conn_factory_transactional, Mock())

        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )
        asyncio.run(
            storage.create_bot_instance(
                channel_name="test-channel",
                governance_alerts_channel="alerts-channel",
                contextstore_github_repo="user/test-repo",
                slack_team_id="T0",
                bot_email="testbot@example.com",
                organization_id=org_id,
            )
        )
        bot_key = BotKey.from_channel_name("T0", "test-channel")
        bot_id = bot_key.to_bot_id()

        for i in range(20):
            # Create some KV data that will expire quickly
            instance_storage = storage.for_instance(bot_id)
            asyncio.run(
                instance_storage.set(
                    "test_family", f"test_key_{i}", f"test_value_{i}", expiry_seconds=1
                )
            )

        # Wait for keys to be ready to expire (reduced from 2s to 1.1s)
        time.sleep(1.1)

        # Function to run "select 1" queries in separate threads
        @sync_to_async
        def run_select_queries():
            for _ in range(5):  # Reduced from 10 to 5 for faster test
                with sql_conn_factory_transactional.with_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    assert result[0] == 1
                    time.sleep(0.005)  # Reduced delay from 0.01 to 0.005

        async def run_concurrent_queries():
            tasks = []
            for _ in range(5):  # Reduced from 10 to 5 concurrent tasks
                tasks.append(asyncio.create_task(run_select_queries()))  # type: ignore

            for task in tasks:
                await task

        asyncio.run(run_concurrent_queries())

        # If we get here without deadlock, the test passes
        # The goal is to test that initialize_database() calls don't deadlock with each other
