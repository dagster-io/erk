"""
Test cases for referral API endpoints.

This module tests:
- POST /api/referral/generate-referral-token
"""

from unittest.mock import Mock

from aiohttp.test_utils import AioHTTPTestCase

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.referral.routes import add_referral_routes


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
        add_referral_routes(app, mock_bot_server)

        return app

    async def test_generate_referral_token_requires_auth(self):
        """Test POST /api/referral/generate-referral-token requires authentication."""
        resp = await self.client.request("POST", "/api/referral/generate-referral-token")
        self.assertEqual(resp.status, 401)

    async def test_copy_referral_link_requires_auth(self):
        """Test POST /api/referral/log-copy-referral-link requires authentication."""
        resp = await self.client.request("POST", "/api/referral/log-copy-referral-link")
        self.assertEqual(resp.status, 401)
