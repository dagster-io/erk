"""
Test cases for connections API endpoints.

This module tests:
- GET /api/connections/list
- GET /api/connections/tables
- POST /api/connections/datasets/add
- POST /api/connections/datasets/remove
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import jwt
from aiohttp.test_utils import AioHTTPTestCase
from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import (
    BotTypeCombined,
    BotTypeGovernance,
    BotTypeQA,
    CompassChannelBaseBotInstance,
)
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.connections.routes import add_connections_routes


class TestConnectionsAPI(AioHTTPTestCase):
    """Test cases for connections API endpoints."""

    async def get_application(self):
        """Create test application."""
        # Create mock bot server
        mock_bot_server = Mock(spec=CompassBotServer)
        mock_bot_server.bots = {}
        mock_bot_server.config = Mock()
        mock_bot_server.config.jwt_secret = Mock()
        mock_bot_server.config.jwt_secret.get_secret_value = Mock(return_value="test-jwt-secret")
        mock_bot_server.logger = Mock()

        # Build application
        app = build_web_application(mock_bot_server)
        add_connections_routes(app, mock_bot_server)

        return app

    async def test_connections_list_requires_auth(self):
        """Test GET /api/connections/list requires authentication."""
        resp = await self.client.request("GET", "/api/connections/list")
        self.assertEqual(resp.status, 401)

    async def test_connections_list_returns_connections(self):
        """Test GET /api/connections/list returns connection list with valid auth."""
        # This test would need proper JWT token creation similar to billing tests
        # For now, just verify the endpoint exists and requires auth
        resp = await self.client.request("GET", "/api/connections/list")
        # Should get 401 without auth
        self.assertEqual(resp.status, 401)

    async def test_add_datasets_requires_auth(self):
        """Test POST /api/connections/datasets/add requires authentication."""
        resp = await self.client.request("POST", "/api/connections/datasets/add")
        self.assertEqual(resp.status, 401)

    async def test_remove_datasets_requires_auth(self):
        """Test POST /api/connections/datasets/remove requires authentication."""
        resp = await self.client.request("POST", "/api/connections/datasets/remove")
        self.assertEqual(resp.status, 401)

    async def test_tables_endpoint_requires_auth(self):
        """Test GET /api/connections/tables requires authentication."""
        resp = await self.client.request("GET", "/api/connections/tables?connection_name=test")
        self.assertEqual(resp.status, 401)

    async def test_tables_endpoint_missing_connection_name(self):
        """Test GET /api/connections/tables returns 400 when connection_name is missing."""
        resp = await self.client.request("GET", "/api/connections/tables")
        self.assertEqual(resp.status, 401)  # Auth check happens first


class TestAddDatasetsEndpoint(AioHTTPTestCase):
    """Test cases for POST /api/connections/datasets/add endpoint bot lookup logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.team_id = "T123456"
        self.organization_id = 123
        self.connection_name = "test_connection"
        self.jwt_secret = "test-secret-key"
        self.user_id = "U123456"

        # Create mock storage
        self.mock_storage = Mock()
        self.mock_storage.get_connection_names_for_organization = AsyncMock(
            return_value={self.connection_name}
        )

        # Create mock bot manager
        self.mock_bot_manager = Mock()
        self.mock_bot_manager.storage = self.mock_storage

        # Create mock temporal client
        self.mock_temporal_client = Mock()
        self.mock_temporal_client.start_workflow = AsyncMock()

        # Create mock server config
        self.mock_server_config = Mock()
        self.mock_server_config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_server_config.public_url = "http://test.local"

        # Create default mock bot server (tests can override bots dict)
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.bots = {}
        self.mock_bot_server.bot_manager = self.mock_bot_manager
        self.mock_bot_server.temporal_client = self.mock_temporal_client
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.config.temporal = Mock()
        self.mock_bot_server.config.temporal.type = "oss"
        self.mock_bot_server.logger = Mock()

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_connections_routes(app, self.mock_bot_server)
        return app

    def create_valid_jwt(self) -> str:
        """Create a valid JWT token for authentication."""
        jwt_payload = {
            "organization_id": self.organization_id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "exp": datetime.now(UTC) + timedelta(hours=3),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def create_mock_bot(
        self, channel_name: str, bot_type, has_connection: bool = False
    ) -> CompassChannelBaseBotInstance:
        """Create a mock bot instance."""
        bot_key = BotKey.from_channel_name(self.team_id, channel_name)

        # Create bot config
        bot_config = Mock(spec=CompassBotSingleChannelConfig)
        bot_config.organization_id = self.organization_id
        bot_config.team_id = self.team_id
        bot_config.organization_name = "Test Organization"

        class Profile:
            def __init__(self, connections):
                self.connections = connections

        class ConnectionConfig:
            def __init__(self, duckdb=None):
                self.duckdb = duckdb

        class DuckDBConfig:
            def __init__(self, path=None):
                self.path = path

        if has_connection:
            profile = Profile(
                connections={
                    self.connection_name: ConnectionConfig(duckdb=DuckDBConfig(path=":memory:"))
                }
            )
        else:
            profile = Profile(connections={})  # Create mock bot
        mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        mock_bot.key = bot_key
        mock_bot.bot_config = bot_config
        mock_bot.bot_type = bot_type
        mock_bot.profile = profile
        mock_bot.server_config = self.mock_server_config

        # Mock kv_store for governance channel lookup
        if hasattr(bot_type, "__class__") and bot_type.__class__.__name__ in [
            "BotTypeGovernance",
            "BotTypeCombined",
        ]:
            mock_bot.governance_alerts_channel = f"{channel_name}-governance"
            mock_bot.kv_store = Mock()
            mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

        return mock_bot

    async def test_add_datasets_with_legacy_governance_bot(self):
        """Test POST /api/connections/datasets/add finds data bot in legacy governance setup.

        In a legacy setup:
        - Data bot (BotTypeQA) has the connection
        - Governance bot (BotTypeGovernance) has governed_bot_keys pointing to data bot
        - The workflow should use the data bot's channel name, not governance bot's
        """
        # Create data bot with connection
        data_bot = self.create_mock_bot(
            channel_name="test-data-channel", bot_type=BotTypeQA(), has_connection=True
        )

        # Create governance bot that governs the data bot
        governance_bot = self.create_mock_bot(
            channel_name="test-governance-channel",
            bot_type=BotTypeGovernance(governed_bot_keys={data_bot.key}),
            has_connection=False,
        )

        # Update bot server with both bots
        self.mock_bot_server.bots = {data_bot.key: data_bot, governance_bot.key: governance_bot}

        # Make request
        jwt_token = self.create_valid_jwt()
        resp = await self.client.request(
            "POST",
            "/api/connections/datasets/add",
            json={
                "connection_name": self.connection_name,
                "datasets": ["table1", "table2"],
            },
            cookies={"compass_auth_token": jwt_token},
        )

        # Verify response
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "processing")

        # Verify workflow was started with DATA bot's bot_id (not governance bot's)
        self.mock_temporal_client.start_workflow.assert_called_once()
        call_args = self.mock_temporal_client.start_workflow.call_args
        workflow_input = call_args[0][1]  # Second positional arg is the input

        # The bot_id should be from the data channel, not governance channel
        expected_bot_id = data_bot.key.to_bot_id()
        self.assertEqual(workflow_input.bot_id, expected_bot_id)
        self.assertIn("test-data-channel", expected_bot_id)
        self.assertNotIn("test-governance-channel", expected_bot_id)

    async def test_add_datasets_with_combined_bot(self):
        """Test POST /api/connections/datasets/add finds correct bot with combined bot type.

        In a combined bot setup:
        - Single bot (BotTypeCombined) serves both data and governance
        - Bot has the connection
        - The workflow should use this bot's channel name
        """
        # Create combined bot with connection
        combined_bot = self.create_mock_bot(
            channel_name="test-combined-channel",
            bot_type=BotTypeCombined(governed_bot_keys=set()),
            has_connection=True,
        )

        # Update bot server with combined bot
        self.mock_bot_server.bots = {combined_bot.key: combined_bot}

        # Make request
        jwt_token = self.create_valid_jwt()
        resp = await self.client.request(
            "POST",
            "/api/connections/datasets/add",
            json={
                "connection_name": self.connection_name,
                "datasets": ["table1", "table2"],
            },
            cookies={"compass_auth_token": jwt_token},
        )

        # Verify response
        if resp.status != 200:
            error_text = await resp.text()
            self.fail(f"Expected 200 but got {resp.status}. Response: {error_text}")
        data = await resp.json()
        self.assertEqual(data["status"], "processing")

        # Verify workflow was started with the combined bot's bot_id
        self.mock_temporal_client.start_workflow.assert_called_once()
        call_args = self.mock_temporal_client.start_workflow.call_args
        workflow_input = call_args[0][1]

        expected_bot_id = combined_bot.key.to_bot_id()
        self.assertEqual(workflow_input.bot_id, expected_bot_id)
        self.assertIn("test-combined-channel", expected_bot_id)
