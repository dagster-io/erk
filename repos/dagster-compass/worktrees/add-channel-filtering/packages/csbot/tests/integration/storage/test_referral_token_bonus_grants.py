"""Tests for referral token bonus grant integration with onboarding."""

import asyncio
import os
import tempfile
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.sqlite import SlackbotSqliteStorage, SqliteConnectionFactory
from csbot.slackbot.webapp.onboarding_steps import (
    CompassChannelsResult,
    ContextstoreResult,
    OrganizationResult,
    SlackTeamResult,
    create_bot_instance_step,
)
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


class TestSqliteReferralTokenBonusGrants:
    """Test referral token bonus grant logic with SQLite storage."""

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
    def setup_organization(self, storage):
        """Set up test organization and bot instance."""
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

            # Insert test organization
            cursor.execute(
                "INSERT INTO organizations (organization_name, organization_industry) VALUES (?, ?)",
                ("Test Organization", "Technology"),
            )
            org_id = cursor.lastrowid

            conn.commit()

        return org_id

    @pytest.fixture
    def mock_bot_server(self, storage, sql_conn_factory):
        """Create a mock bot server with storage."""
        bot_server = MagicMock()
        bot_server.bot_manager.storage = storage
        bot_server.sql_conn_factory = sql_conn_factory
        bot_server.logger = MagicMock()
        bot_server.bots = {}
        return bot_server

    @pytest.fixture
    def mock_onboarding_context(self, sql_conn_factory):
        """Create a mock onboarding context."""
        ctx = AsyncMock()
        ctx.mark_step_completed = AsyncMock()
        ctx.analytics_store = SlackbotAnalyticsStore(sql_conn_factory)
        return ctx

    def test_bonus_grant_amounts(
        self,
        storage,
        sql_conn_factory,
        setup_organization,
        mock_bot_server,
        mock_onboarding_context,
    ):
        """Test that tokens with various bonus amounts create appropriate grants via create_bot_instance_step."""
        org_id = setup_organization

        # Create tokens before async context
        token1 = "token-150"
        storage.create_invite_token(token1, is_single_use=False, consumer_bonus_answers=150)
        token2 = "token-500"
        storage.create_invite_token(token2, is_single_use=False, consumer_bonus_answers=500)

        async def run_test():
            # Test 150 bonus
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C123",
                    compass_channel_name="test-compass",
                    governance_channel_id="C456",
                    governance_channel_name="test-governance",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T12345",
                    team_domain="test-domain",
                    team_name="Test Team",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test@example.com",
                token=token1,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

            # Test 500 custom bonus
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C789",
                    compass_channel_name="test-compass-2",
                    governance_channel_id="C012",
                    governance_channel_name="test-governance-2",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo-2",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T67890",
                    team_domain="test-domain-2",
                    team_name="Test Team 2",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test2@example.com",
                token=token2,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

        asyncio.run(run_test())

        # Verify both grants were created
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = ?
                ORDER BY answer_count
            """,
                (org_id,),
            )
            grants = cursor.fetchall()
            assert len(grants) == 2
            assert grants[0][0] == 150
            assert grants[1][0] == 500

    def test_zero_bonus_no_grant_created(
        self,
        storage,
        sql_conn_factory,
        setup_organization,
        mock_bot_server,
        mock_onboarding_context,
    ):
        """Test that zero bonus token does not create a grant via create_bot_instance_step."""
        org_id = setup_organization

        # Create token before async context
        token = "zero-bonus-token"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=0)

        async def run_test():
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C123",
                    compass_channel_name="test-compass",
                    governance_channel_id="C456",
                    governance_channel_name="test-governance",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T12345",
                    team_domain="test-domain",
                    team_name="Test Team",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test@example.com",
                token=token,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

        asyncio.run(run_test())

        # Verify NO grant was created
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = ?
            """,
                (org_id,),
            )
            grants = cursor.fetchall()
            assert len(grants) == 0, "No grant should be created for zero bonus"

    def test_multi_use_token_grants_to_each_org(self, storage, sql_conn_factory):
        """Test that multi-use token grants bonus to each organization."""
        # Create two organizations
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_name TEXT NOT NULL,
                    organization_industry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("INSERT INTO organizations (organization_name) VALUES (?)", ("Org 1",))
            org1_id = cursor.lastrowid

            cursor.execute("INSERT INTO organizations (organization_name) VALUES (?)", ("Org 2",))
            org2_id = cursor.lastrowid

            conn.commit()

        # Create multi-use token
        token = "multi-use-token"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=150)

        # Get token data
        tokens = asyncio.run(storage.list_invite_tokens())
        token_data = next((t for t in tokens if t.token == token), None)
        assert token_data is not None

        analytics_store = SlackbotAnalyticsStore(sql_conn_factory)

        # First org uses token
        if token_data.consumer_bonus_answers > 0:
            asyncio.run(
                analytics_store.create_bonus_answer_grant(
                    org1_id, token_data.consumer_bonus_answers, "sign-up bonus"
                )
            )

        # Second org uses same token
        if token_data.consumer_bonus_answers > 0:
            asyncio.run(
                analytics_store.create_bonus_answer_grant(
                    org2_id, token_data.consumer_bonus_answers, "sign-up bonus"
                )
            )

        # Verify both orgs got grants
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = ?
            """,
                (org1_id,),
            )
            org1_grants = cursor.fetchall()
            assert len(org1_grants) == 1
            assert org1_grants[0][0] == 150

            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = ?
            """,
                (org2_id,),
            )
            org2_grants = cursor.fetchall()
            assert len(org2_grants) == 1
            assert org2_grants[0][0] == 150


@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="PostgreSQL dependencies not available")
class TestPostgresqlReferralTokenBonusGrants:
    """Test referral token bonus grant logic with PostgreSQL storage."""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Session-scoped PostgreSQL container for testing."""
        if test_db_url := os.environ.get("TEST_DATABASE_URL"):
            if test_db_url.startswith("postgresql://"):
                yield test_db_url
                return

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
    def setup_organization(self, storage):
        """Set up test organization."""
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry)
                VALUES (%s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology"),
            )
            org_id = cursor.fetchone()[0]

            conn.commit()

        return org_id

    @pytest.fixture
    def mock_bot_server(self, storage, sql_conn_factory):
        """Create a mock bot server with storage."""
        bot_server = MagicMock()
        bot_server.bot_manager.storage = storage
        bot_server.sql_conn_factory = sql_conn_factory
        bot_server.logger = MagicMock()
        bot_server.bots = {}
        return bot_server

    @pytest.fixture
    def mock_onboarding_context(self, sql_conn_factory):
        """Create a mock onboarding context."""
        ctx = AsyncMock()
        ctx.mark_step_completed = AsyncMock()
        ctx.analytics_store = SlackbotAnalyticsStore(sql_conn_factory)
        return ctx

    def test_bonus_grant_amounts(
        self,
        storage,
        sql_conn_factory,
        setup_organization,
        mock_bot_server,
        mock_onboarding_context,
    ):
        """Test that tokens with various bonus amounts create appropriate grants via create_bot_instance_step."""
        org_id = setup_organization

        # Create tokens before async context
        token1 = "token-150"
        storage.create_invite_token(token1, is_single_use=False, consumer_bonus_answers=150)
        token2 = "token-500"
        storage.create_invite_token(token2, is_single_use=False, consumer_bonus_answers=500)

        async def run_test():
            # Test 150 bonus
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C123",
                    compass_channel_name="test-compass",
                    governance_channel_id="C456",
                    governance_channel_name="test-governance",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T12345",
                    team_domain="test-domain",
                    team_name="Test Team",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test@example.com",
                token=token1,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

            # Test 500 custom bonus
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C789",
                    compass_channel_name="test-compass-2",
                    governance_channel_id="C012",
                    governance_channel_name="test-governance-2",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo-2",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T67890",
                    team_domain="test-domain-2",
                    team_name="Test Team 2",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test2@example.com",
                token=token2,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

        asyncio.run(run_test())

        # Verify both grants were created
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = %s
                ORDER BY answer_count
            """,
                (org_id,),
            )
            grants = cursor.fetchall()
            assert len(grants) == 2
            assert grants[0][0] == 150
            assert grants[1][0] == 500

    def test_zero_bonus_no_grant_created(
        self,
        storage,
        sql_conn_factory,
        setup_organization,
        mock_bot_server,
        mock_onboarding_context,
    ):
        """Test that zero bonus token does not create a grant via create_bot_instance_step."""
        org_id = setup_organization

        # Create token before async context
        token = "zero-bonus-token"
        storage.create_invite_token(token, is_single_use=False, consumer_bonus_answers=0)

        async def run_test():
            await create_bot_instance_step(
                ctx=mock_onboarding_context,
                compass_channels_result=CompassChannelsResult(
                    compass_channel_id="C123",
                    compass_channel_name="test-compass",
                    governance_channel_id="C456",
                    governance_channel_name="test-governance",
                ),
                contextstore_result=ContextstoreResult(
                    contextstore_repo_name="test-repo",
                    repo_result={},
                ),
                slack_team_result=SlackTeamResult(
                    team_id="T12345",
                    team_domain="test-domain",
                    team_name="Test Team",
                ),
                organization_result=OrganizationResult(
                    organization_id=org_id,
                    analytics_store=SlackbotAnalyticsStore(sql_conn_factory),
                ),
                email="test@example.com",
                token=token,
                has_valid_token=True,
                bot_server=mock_bot_server,
            )

        asyncio.run(run_test())

        # Verify NO grant was created
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT answer_count FROM bonus_answer_grants
                WHERE organization_id = %s
            """,
                (org_id,),
            )
            grants = cursor.fetchall()
            assert len(grants) == 0, "No grant should be created for zero bonus"


if __name__ == "__main__":
    pytest.main([__file__])
