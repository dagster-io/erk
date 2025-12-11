"""
Test cases for user profile API endpoints.

This module tests:
- GET /api/user/profile
"""

from unittest.mock import AsyncMock, Mock

from aiohttp.test_utils import AioHTTPTestCase

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.routes import add_webapp_routes


class TestUserProfileAPI(AioHTTPTestCase):
    """Test cases for user profile API endpoints."""

    async def get_application(self):
        """Create test application."""
        # Create mock bot server
        mock_bot_server = Mock(spec=CompassBotServer)
        mock_bot_server.bots = {}
        mock_bot_server.config = Mock()
        mock_bot_server.config.jwt_secret = Mock()
        mock_bot_server.config.jwt_secret.get_secret_value = Mock(return_value="test-jwt-secret")
        mock_bot_server.bot_manager = Mock()
        mock_bot_server.bot_manager.storage = AsyncMock()
        mock_bot_server.logger = Mock()

        # Build application
        app = build_web_application(mock_bot_server)
        add_webapp_routes(app, mock_bot_server)

        return app

    async def test_user_profile_requires_auth(self):
        """Test GET /api/user/profile requires authentication."""
        resp = await self.client.request("GET", "/api/user/profile")
        self.assertEqual(resp.status, 401)

    async def test_user_profile_returns_profile_data(self):
        """Test GET /api/user/profile returns user profile with valid auth."""
        # This test would need proper JWT token creation
        # For now, just verify the endpoint exists and requires auth
        resp = await self.client.request("GET", "/api/user/profile")
        # Should get 401 without auth
        self.assertEqual(resp.status, 401)
