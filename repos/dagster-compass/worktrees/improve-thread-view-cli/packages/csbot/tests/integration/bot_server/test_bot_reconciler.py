"""Tests for CompassBotReconciler with filtering and reconciliation logic."""

import asyncio
import base64
import os
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from cryptography.fernet import Fernet

from csbot.config.database_instance_loader import DatabaseBotInstanceLoader
from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import BotTypeQA
from csbot.slackbot.config import DatabaseConfig, UnsupportedKekConfig
from csbot.slackbot.storage.factory import create_storage as base_create_storage
from csbot.slackbot.storage.interface import SqlConnectionFactory
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory
from csbot.slackbot.storage.schema_changes import SchemaManager


def create_storage(conn_factory: SqlConnectionFactory):
    return base_create_storage(conn_factory, kek_config=UnsupportedKekConfig())


pytest_plugins = ("pytest_asyncio",)

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")


@pytest.fixture(scope="session")
def encryption_setup():
    """Set up encryption key for all tests in this session."""
    key = Fernet.generate_key()
    encoded_key = base64.urlsafe_b64encode(key).decode()
    os.environ["SECRET_ENCRYPTION_KEY"] = encoded_key
    fernet = Fernet(key)
    yield fernet
    if "SECRET_ENCRYPTION_KEY" in os.environ:
        del os.environ["SECRET_ENCRYPTION_KEY"]


@pytest.fixture
def encrypted_tokens(encryption_setup):
    """Create encrypted tokens for testing."""
    fernet = encryption_setup
    tokens = {
        "SLACK_BOT_TOKEN_T1111": fernet.encrypt(b"xoxb-test-token-111").decode(),
        "SLACK_BOT_TOKEN_T2222": fernet.encrypt(b"xoxb-test-token-222").decode(),
    }
    for env_var, encrypted_value in tokens.items():
        os.environ[env_var] = encrypted_value
    yield tokens
    for env_var in tokens:
        if env_var in os.environ:
            del os.environ[env_var]


@pytest.fixture
def sql_conn_factory(postgres_container):
    """Create a PostgreSQL connection factory for testing."""
    return PostgresqlConnectionFactory.from_db_config(DatabaseConfig.from_uri(postgres_container))


@pytest.fixture
def test_schema(sql_conn_factory):
    """Create test schema using SchemaManager."""
    with sql_conn_factory.with_conn() as conn:
        schema_manager = SchemaManager()
        schema_manager.apply_all_changes(conn)
        conn.commit()
        yield
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        conn.commit()


@pytest.fixture
def mock_config():
    """Create a mock CompassBotServerConfig."""
    config = Mock()
    config.github = Mock()
    config.github.get_auth_source = Mock(return_value=Mock())

    # Properly configure AI config
    config.ai_config = Mock()
    config.ai_config.provider = "anthropic"
    config.ai_config.model = "claude-3-5-sonnet-20241022"
    config.ai_config.api_key = Mock()
    config.ai_config.api_key.get_secret_value = Mock(return_value="test-api-key")

    config.compass_bot_token = Mock()
    config.compass_bot_token.get_secret_value = Mock(return_value="xoxb-test-token")
    return config


@pytest.fixture
def mock_secret_store():
    """Create a mock SecretStore."""
    return Mock()


@pytest.fixture
def mock_temporal_client():
    """Create a mock Temporal client."""
    return AsyncMock()


@pytest.fixture
def bot_loader(sql_conn_factory, test_schema):
    """Create a DatabaseBotInstanceLoader for testing."""
    storage = create_storage(sql_conn_factory)
    template_context = {"env": "test"}

    def get_template_context_for_org(org_id: int) -> dict[str, Any]:
        return {**template_context, "org_id": org_id}

    return DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)


def _insert_test_organization_sync(conn, org_name: str = "Test Org") -> int:
    """Helper to insert a test organization and return its ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO organizations (organization_name, organization_industry) VALUES (%s, %s) RETURNING organization_id",
        (org_name, "Technology"),
    )
    return cursor.fetchone()[0]


def _insert_bot_instance_sync(
    conn, team_id: str, channel_name: str, org_id: int, governance_channel: str | None = None
) -> None:
    """Helper to insert a bot instance."""
    governance_channel = governance_channel or f"{channel_name}-governance"
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bot_instances (
            channel_name, bot_email, contextstore_github_repo,
            governance_alerts_channel, slack_team_id, organization_id
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            channel_name,
            f"bot@{channel_name}.com",
            "user/repo",
            governance_channel,
            team_id,
            org_id,
        ),
    )


def _insert_slack_token_sync(conn, team_id: str) -> None:
    """Helper to insert a Slack bot token."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name) VALUES (%s, %s)",
        (team_id, f"SLACK_BOT_TOKEN_{team_id}"),
    )


async def insert_test_organization(sql_conn_factory, org_name: str = "Test Org") -> int:
    """Async helper to insert a test organization and return its ID."""

    def _insert():
        with sql_conn_factory.with_conn() as conn:
            org_id = _insert_test_organization_sync(conn, org_name)
            conn.commit()
            return org_id

    return await asyncio.to_thread(_insert)


async def insert_bot_instance(
    sql_conn_factory,
    team_id: str,
    channel_name: str,
    org_id: int,
    governance_channel: str | None = None,
) -> None:
    """Async helper to insert a bot instance."""
    governance_channel = governance_channel or f"{channel_name}-governance"

    def _insert():
        with sql_conn_factory.with_conn() as conn:
            _insert_bot_instance_sync(conn, team_id, channel_name, org_id, governance_channel)
            conn.commit()

    await asyncio.to_thread(_insert)


async def insert_slack_token(sql_conn_factory, team_id: str) -> None:
    """Async helper to insert a Slack bot token."""

    def _insert():
        with sql_conn_factory.with_conn() as conn:
            _insert_slack_token_sync(conn, team_id)
            conn.commit()

    await asyncio.to_thread(_insert)


async def delete_bot_instance(sql_conn_factory, channel_name: str) -> None:
    """Async helper to delete a bot instance."""

    def _delete():
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bot_instances WHERE channel_name = %s", (channel_name,))
            conn.commit()

    await asyncio.to_thread(_delete)


# Shared mock github_config that all mock bots will use
# This ensures that bots sharing a governance channel have the "same" github_config
_SHARED_MOCK_GITHUB_CONFIG = Mock(spec=[])


def create_mock_bot(key: BotKey, governance_channel: str = "governance") -> Mock:
    """Create a mock bot instance for testing."""
    mock_bot = Mock()
    mock_bot.key = key
    mock_bot.bot_config = Mock()
    mock_bot.bot_config.governance_alerts_channel = governance_channel
    mock_bot.bot_config.should_restart = Mock(return_value=False)
    mock_bot.bot_type = BotTypeQA()
    mock_bot.governance_alerts_channel = governance_channel
    # Use shared github_config so all mock bots pass validation checks
    mock_bot.github_config = _SHARED_MOCK_GITHUB_CONFIG
    return mock_bot


def create_bot_mocking_patches(reconciler):
    """Create mock patches for bot construction to avoid real bot instantiation."""

    async def mock_start_bot(key, bot_config, auth_source):
        mock_bot = create_mock_bot(key, bot_config.governance_alerts_channel)
        mock_bot.bot_config = bot_config
        await reconciler._add_and_start_bot_instance(key, mock_bot)
        return mock_bot

    def mock_construct_governance_bots(
        storage, qa_bots, selected_governance_channels, server_config
    ):
        # Create mock governance bots for each unique (team_id, governance_channel) pair
        governance_bots = []
        if qa_bots:
            # Group by team_id and governance_channel
            governance_keys = {(bot.key.team_id, bot.governance_alerts_channel) for bot in qa_bots}
            for team_id, channel in governance_keys:
                key = BotKey(team_id=team_id, channel_name=channel)
                mock_bot = create_mock_bot(key, channel)
                # Governance bots need a bot_config with connections for logging
                mock_bot.bot_config.connections = []
                governance_bots.append(mock_bot)
        return governance_bots

    return [
        patch.object(reconciler, "_start_bot_instance", side_effect=mock_start_bot),
        patch(
            "csbot.slackbot.channel_bot.bot_factory.CompassChannelBotInstanceFactory.construct_governance_bots",
            side_effect=mock_construct_governance_bots,
        ),
    ]


class TestBotReconcilerDiscovery:
    """Test bot reconciler discovery with and without channel filtering."""

    @pytest.mark.asyncio
    async def test_discover_all_bots_no_filter(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test discovering all bots when no channel filter is provided."""
        # Insert test data - 3 bot instances
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-b", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-c", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,  # Skip background tasks in tests
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover all bots
            await reconciler.discover_and_update_bots()

        # All 3 QA bots + 1 governance bot should be active
        assert len(reconciler.active_bots) == 6
        assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
        assert BotKey(team_id="T1111", channel_name="channel-b") in reconciler.active_bots
        assert BotKey(team_id="T1111", channel_name="channel-c") in reconciler.active_bots
        assert (
            BotKey(team_id="T1111", channel_name="channel-a-governance") in reconciler.active_bots
        )
        assert (
            BotKey(team_id="T1111", channel_name="channel-b-governance") in reconciler.active_bots
        )
        assert (
            BotKey(team_id="T1111", channel_name="channel-c-governance") in reconciler.active_bots
        )

    @pytest.mark.asyncio
    async def test_discover_single_channel_with_filter(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test discovering only a specific channel when filtered."""
        # Insert test data - 3 bot instances
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-b", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-c", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover only channel-b
            await reconciler.discover_and_update_bots_for_keys(
                [BotKey(team_id="T1111", channel_name="channel-b")]
            )

            # Only channel-b + governance bot should be active
            assert len(reconciler.active_bots) == 2
            assert BotKey(team_id="T1111", channel_name="channel-b") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-b-governance")
                in reconciler.active_bots
            )
            # Other channels should NOT be loaded
            assert BotKey(team_id="T1111", channel_name="channel-a") not in reconciler.active_bots
            assert BotKey(team_id="T1111", channel_name="channel-c") not in reconciler.active_bots

    @pytest.mark.asyncio
    async def test_filtered_discovery_does_not_remove_other_bots(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test that filtered discovery does not remove bots outside the filter scope."""
        # Insert test data - 3 bot instances
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-b", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-c", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # First, discover all bots
            await reconciler.discover_and_update_bots()
            assert len(reconciler.active_bots) == 6  # 3 QA + 3 governance

            # Now, delete channel-b from the database
            await delete_bot_instance(sql_conn_factory, "channel-b")

            # Run filtered discovery for channel-b only
            await reconciler.discover_and_update_bots_for_keys(
                [BotKey(team_id="T1111", channel_name="channel-b")]
            )

            # channel-b should be removed, but channel-a and channel-c should remain
            assert len(reconciler.active_bots) == 5  # TODO we didn't remove channel-b-governance
            assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-a-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-c") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-c-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-b") not in reconciler.active_bots

    @pytest.mark.asyncio
    async def test_full_discovery_removes_deleted_bots(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test that full discovery removes all deleted bots."""
        # Insert test data - 3 bot instances
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-b", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-c", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # First, discover all bots
            await reconciler.discover_and_update_bots()
            assert len(reconciler.active_bots) == 6  # 3 QA + 3 governance

            # Delete channel-b from the database
            await delete_bot_instance(sql_conn_factory, "channel-b")

            # Run full discovery (no filter)
            await reconciler.discover_and_update_bots()

            # channel-b should be removed
            assert len(reconciler.active_bots) == 4
            assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-a-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-c") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-c-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-b") not in reconciler.active_bots

    @pytest.mark.asyncio
    async def test_add_new_bot_with_filter(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test adding a new bot instance using filtered discovery."""
        # Insert initial data - 2 bot instances
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-b", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover existing bots
            await reconciler.discover_and_update_bots()
            assert len(reconciler.active_bots) == 4  # 2 QA + 2 governance

            # Add a new bot instance to the database
            await insert_bot_instance(sql_conn_factory, "T1111", "channel-c", org_id)

            # Run filtered discovery for the new channel
            await reconciler.discover_and_update_bots_for_keys(
                [BotKey(team_id="T1111", channel_name="channel-c")]
            )

            # New channel should be added, existing channels should remain
            assert len(reconciler.active_bots) == 6  # 3 QA + 3 governance
            assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-a-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-b") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-b-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T1111", channel_name="channel-c") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-c-governance")
                in reconciler.active_bots
            )

    @pytest.mark.asyncio
    async def test_self_governed_channel(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test bot with self-governed channel (governance_channel == channel_name)."""
        # Insert a bot that governs itself
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        # Self-governed: governance_channel is the same as channel_name
        await insert_bot_instance(
            sql_conn_factory, "T1111", "self-governed", org_id, governance_channel="self-governed"
        )

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover the self-governed bot
            await reconciler.discover_and_update_bots()

            # Only 1 bot should exist (no separate governance bot)
            assert len(reconciler.active_bots) == 1
            assert BotKey(team_id="T1111", channel_name="self-governed") in reconciler.active_bots

    @pytest.mark.asyncio
    async def test_multiple_teams(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test discovery with bots from multiple Slack teams."""
        # Insert bots from two different teams
        org1_id = await insert_test_organization(sql_conn_factory, "Org 1")
        org2_id = await insert_test_organization(sql_conn_factory, "Org 2")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_slack_token(sql_conn_factory, "T2222")
        await insert_bot_instance(sql_conn_factory, "T1111", "team1-channel", org1_id)
        await insert_bot_instance(sql_conn_factory, "T2222", "team2-channel", org2_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover all bots
            await reconciler.discover_and_update_bots()

            # 2 QA bots + 2 governance bots
            assert len(reconciler.active_bots) == 4
            assert BotKey(team_id="T1111", channel_name="team1-channel") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="team1-channel-governance")
                in reconciler.active_bots
            )
            assert BotKey(team_id="T2222", channel_name="team2-channel") in reconciler.active_bots
            assert (
                BotKey(team_id="T2222", channel_name="team2-channel-governance")
                in reconciler.active_bots
            )

    @pytest.mark.asyncio
    async def test_filtered_discovery_with_nonexistent_channel(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test filtered discovery when the specified channel does not exist."""
        # Insert one bot instance
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(sql_conn_factory, "T1111", "channel-a", org_id)

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # First, discover all bots
            await reconciler.discover_and_update_bots()
            assert len(reconciler.active_bots) == 2  # 1 QA + 1 governance

            # Try to discover a non-existent channel
            await reconciler.discover_and_update_bots_for_keys(
                [BotKey(team_id="T1111", channel_name="nonexistent-channel")]
            )

            # Existing bots should remain unchanged
            assert len(reconciler.active_bots) == 2
            assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
            assert (
                BotKey(team_id="T1111", channel_name="channel-a-governance")
                in reconciler.active_bots
            )

    @pytest.mark.asyncio
    async def test_empty_database(
        self,
        sql_conn_factory,
        test_schema,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test discovery with an empty database."""
        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Discover bots from empty database
        await reconciler.discover_and_update_bots()

        # No bots should be active
        assert len(reconciler.active_bots) == 0

    @pytest.mark.asyncio
    async def test_governance_bot_updates_on_filtered_discovery(
        self,
        sql_conn_factory,
        test_schema,
        encrypted_tokens,
        mock_config,
        mock_secret_store,
        mock_temporal_client,
        bot_loader,
    ):
        """Test that governance bots are properly updated during filtered discovery."""
        # Insert multiple bots sharing the same governance channel
        org_id = await insert_test_organization(sql_conn_factory, "Test Org")
        await insert_slack_token(sql_conn_factory, "T1111")
        await insert_bot_instance(
            sql_conn_factory, "T1111", "channel-a", org_id, governance_channel="gov"
        )
        await insert_bot_instance(
            sql_conn_factory, "T1111", "channel-b", org_id, governance_channel="gov"
        )

        storage = create_storage(sql_conn_factory)
        reconciler = CompassBotReconciler(
            config=mock_config,
            secret_store=mock_secret_store,
            storage=storage,
            bot_loader=bot_loader,
            temporal_client=mock_temporal_client,
            skip_background_tasks=True,
        )

        # Mock bot construction to return mock bots instead of real ones
        patches = create_bot_mocking_patches(reconciler)
        with patches[0], patches[1]:
            # Discover all bots
            await reconciler.discover_and_update_bots()
            assert len(reconciler.active_bots) == 3  # 2 QA + 1 governance

            # Run filtered discovery for channel-a only
            await reconciler.discover_and_update_bots_for_keys(
                [BotKey(team_id="T1111", channel_name="channel-a")]
            )

            # All bots should still be active, governance bot should be updated
            assert len(reconciler.active_bots) == 3
            assert BotKey(team_id="T1111", channel_name="channel-a") in reconciler.active_bots
            assert BotKey(team_id="T1111", channel_name="channel-b") in reconciler.active_bots
            assert BotKey(team_id="T1111", channel_name="gov") in reconciler.active_bots
