"""
Base test class for channels webapp functionality.

This module provides common setup and utilities for channels tests including:
- JWT validation and cookie handling setup
- Mock bot server and governance bot configuration
- Common test fixtures and helper methods
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import jwt
from aiohttp.test_utils import AioHTTPTestCase
from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import (
    CompassChannelBaseBotInstance,
)
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.storage.interface import OrgUser, PlanLimits
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.channels.routes import add_channels_routes

# Export for use by other test modules
__all__ = ["BaseChannelsTest"]


class BaseChannelsTest(AioHTTPTestCase):
    """Base test class for channels webapp functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team_id = "T123456"
        self.jwt_secret = "test-secret-key-for-channels"
        self.organization_id = 123
        self.user_id = "U123456"

        # Create mock OrgUser for authenticated user
        self.mock_org_user = OrgUser(
            id=1,
            slack_user_id=self.user_id,
            email="test@example.com",
            organization_id=self.organization_id,
            is_org_admin=True,
            name="Test User",
        )

        # Create mock self-governing channel bot keys
        self.governed_bot_key_1 = BotKey(team_id=self.team_id, channel_name="channel-1")
        self.governed_bot_key_2 = BotKey(team_id=self.team_id, channel_name="channel-2")

        # Create mock governed bots (Combined type bots for self-governing channels)
        from csbot.slackbot.channel_bot.bot import BotTypeCombined

        self.mock_governed_bot_1 = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_governed_bot_1.key = self.governed_bot_key_1
        # Use Combined type to simulate self-governing channels
        self.mock_governed_bot_1.bot_type = BotTypeCombined(
            governed_bot_keys=set([self.governed_bot_key_1])
        )
        # Add bot_config with organization_id and team_id
        self.mock_governed_bot_1.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_governed_bot_1.bot_config.organization_id = self.organization_id
        self.mock_governed_bot_1.bot_config.team_id = self.team_id
        self.mock_governed_bot_1.bot_config.organization_name = "Test Organization"
        self.mock_governed_bot_1.bot_config.contextstore_github_repo = "test-org/test-repo"
        self.mock_governed_bot_1.governance_alerts_channel = "channel-1"  # Self-governing

        self.mock_governed_bot_2 = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_governed_bot_2.key = self.governed_bot_key_2
        # Use Combined type to simulate self-governing channels
        self.mock_governed_bot_2.bot_type = BotTypeCombined(
            governed_bot_keys=set([self.governed_bot_key_2])
        )
        # Add bot_config with organization_id and team_id
        self.mock_governed_bot_2.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_governed_bot_2.bot_config.organization_id = self.organization_id
        self.mock_governed_bot_2.bot_config.team_id = self.team_id
        self.mock_governed_bot_2.bot_config.organization_name = "Test Organization"
        self.mock_governed_bot_2.bot_config.contextstore_github_repo = "test-org/test-repo"
        self.mock_governed_bot_2.governance_alerts_channel = "channel-2"  # Self-governing

        # Use first bot as the "governance" bot for auth (any combined bot can serve this role)
        self.bot_key = self.governed_bot_key_1
        self.mock_bot = self.mock_governed_bot_1
        self.mock_config = self.mock_governed_bot_1.bot_config

        # Mock storage
        self.mock_storage = Mock()
        self.mock_storage.get_connection_names_for_bot = AsyncMock(return_value=["conn1", "conn2"])
        self.mock_storage.get_connection_names_for_organization = AsyncMock(
            return_value=["conn1", "conn2", "conn3"]
        )
        self.mock_storage.reconcile_bot_connection = AsyncMock()
        self.mock_storage.set_plan_limits = AsyncMock()
        self.mock_storage.get_plan_limits = AsyncMock(
            return_value=PlanLimits(
                base_num_answers=100,
                allow_overage=True,
                num_channels=3,
                allow_additional_channels=False,
            )
        )
        # Mock OrgUser retrieval methods
        self.mock_storage.get_org_user_by_id = AsyncMock(return_value=self.mock_org_user)
        self.mock_storage.get_org_user_by_slack_user_id = AsyncMock(return_value=self.mock_org_user)

        # Mock bot manager
        self.mock_bot_manager = Mock()
        self.mock_bot_manager.storage = self.mock_storage
        self.mock_bot_manager.discover_and_update_bots_for_keys = AsyncMock()

        # Mock bot server
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.config.public_url = "https://test.example.com"
        self.mock_bot_server.config.compass_dev_tools_bot_token = SecretStr(
            "xoxb-test-dev-tools-token"
        )
        self.mock_bot_server.config.slack_admin_token = SecretStr("xoxp-test-admin-token")
        self.mock_bot_server.config.compass_bot_token = SecretStr("xoxb-test-compass-token")

        self.mock_bot_server.bots = {
            self.governed_bot_key_1: self.mock_governed_bot_1,
            self.governed_bot_key_2: self.mock_governed_bot_2,
        }
        self.mock_bot_server.bot_manager = self.mock_bot_manager
        self.mock_bot_server.logger = Mock()

        # Mock canonicalize_bot_key
        async def mock_canonicalize_bot_key(key: BotKey) -> BotKey:
            return key

        self.mock_bot_server.canonicalize_bot_key = mock_canonicalize_bot_key

        # Mock get_plan_limits_from_cache_or_bail
        self.mock_bot_server.get_plan_limits_from_cache_or_bail = AsyncMock(
            return_value=PlanLimits(
                base_num_answers=100,
                allow_overage=True,
                num_channels=3,
                allow_additional_channels=False,
            )
        )

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_channels_routes(app, self.mock_bot_server)
        return app

    def create_valid_channels_jwt(
        self,
        view_channels: bool = True,
        manage_channels: bool = True,
        exp_hours: int = 3,
        user_id: str | None = None,
    ):
        """Create a valid JWT token for compass_auth cookie (user-based auth).

        This creates a token with org_user_id which is used by the compass_auth cookie
        for proper permission-based authentication. Also includes user_id for backward
        compatibility with routes that need the Slack user ID for attribution.
        """
        if user_id is None:
            user_id = self.user_id

        jwt_payload = {
            "organization_id": self.organization_id,
            "org_user_id": self.mock_org_user.id,
            "user_id": user_id,  # Include Slack user ID for attribution
            "team_id": self.team_id,
            "exp": datetime.now(UTC) + timedelta(hours=exp_hours),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def create_expired_channels_jwt(self, user_id: str | None = None):
        """Create an expired JWT token for compass_auth cookie."""
        if user_id is None:
            user_id = self.user_id

        jwt_payload = {
            "organization_id": self.organization_id,
            "org_user_id": self.mock_org_user.id,
            "team_id": self.team_id,
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def get_channels_cookies(self, jwt_token: str) -> dict[str, str]:
        """Get cookies dict for channels requests.

        Uses compass_auth cookie name which is used for user-based authentication
        with proper permission checking.
        """
        return {"compass_auth": jwt_token}
