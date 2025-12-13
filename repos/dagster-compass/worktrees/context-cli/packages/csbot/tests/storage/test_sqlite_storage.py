import asyncio
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from csbot.slackbot.config import PlaintextKekConfig
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.slackbot.storage.interface import (
    SlackbotInstanceStorage,
    SqlConnectionFactory,
)
from csbot.slackbot.storage.sqlite import (
    SlackbotInstanceSqliteStorage,
    SlackbotSqliteStorage,
    SqliteConnectionFactory,
)
from csbot.utils.time import SecondsNow

from .slackbot_storage_test_base import SlackbotStorageTestBase
from .test_storage_base import StorageTestBase


class TestSlackbotInstanceSqliteStorage(StorageTestBase):
    """Test suite for SlackbotInstanceSqliteStorage using the shared storage test base."""

    @pytest.fixture
    def sql_conn_factory(self) -> SqlConnectionFactory:
        """Create a fresh in-memory SQLite connection factory for each test."""
        return SqliteConnectionFactory.temporary_for_testing()

    @pytest.fixture
    def storage(self, sql_conn_factory: SqlConnectionFactory) -> SlackbotInstanceStorage:
        """Create a storage instance with a test bot ID."""
        return SlackbotInstanceSqliteStorage(sql_conn_factory, "test_bot_id", Mock())

    @pytest.fixture
    def storage2(self, sql_conn_factory: SqlConnectionFactory) -> SlackbotInstanceStorage:
        """Create a second storage instance with a different bot ID for isolation tests."""
        return SlackbotInstanceSqliteStorage(sql_conn_factory, "test_bot_id_2", Mock())

    def _create_storage(
        self, sql_conn_factory: SqlConnectionFactory, bot_id: str, seconds_now: SecondsNow
    ) -> SlackbotInstanceStorage:
        """Create a storage instance for the given bot ID."""
        return SlackbotInstanceSqliteStorage(sql_conn_factory, bot_id, Mock(), seconds_now)


class TestSlackbotSqliteStorage(SlackbotStorageTestBase):
    """Test suite for SlackbotSqliteStorage organization and bot management functionality."""

    @pytest.fixture
    def sql_conn_factory(self) -> SqlConnectionFactory:
        """Create a fresh in-memory SQLite connection factory for each test."""
        return SqliteConnectionFactory.temporary_for_testing()

    @pytest.fixture
    def storage(self, sql_conn_factory: SqlConnectionFactory) -> SlackbotSqliteStorage:
        """Create a SlackbotSqliteStorage instance."""
        return SlackbotSqliteStorage(
            sql_conn_factory,
            KekProvider(
                PlaintextKekConfig(key=SecretStr("fNnln2pTP2QRjtD644VZ0kzE20cfQvrU4ZnqcZK0t_8="))
            ),
        )

    def test_add_connection_null_dialect(self, storage):
        """Test adding connection with null additional_sql_dialect."""
        # Create an organization first
        org_id = asyncio.run(
            storage.create_organization(
                name="Test Organization",
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )
        )

        # Add connection with null dialect
        asyncio.run(
            storage.add_connection(
                organization_id=org_id,
                connection_name="test_conn",
                url="postgresql://localhost:5432/test",
                additional_sql_dialect=None,
            )
        )

        # Verify the connection was added with null dialect
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT additional_sql_dialect
                FROM connections WHERE organization_id = ? AND connection_name = ?
                """,
                (org_id, "test_conn"),
            )
            result = cursor.fetchone()

            assert result is not None
            assert result[0] is None
