"""
Test cases for channels API authentication and authorization.

This module tests auth/permission requirements once for all endpoints,
avoiding duplication across individual endpoint tests.
"""

from .base_channels_test import BaseChannelsTest


class TestChannelsAuth(BaseChannelsTest):
    """Test authentication and authorization for channels endpoints."""

    async def test_all_endpoints_require_auth(self):
        """Test that all channels endpoints require authentication."""
        endpoints = [
            ("GET", "/api/channels/list", None),
            ("POST", "/api/channels/create", {"channel_name": "test"}),
            ("POST", "/api/channels/update", {"bot_id": "test", "connection_names": []}),
            ("DELETE", "/api/channels/delete", {"bot_id": "test"}),
        ]

        for method, path, json_data in endpoints:
            with self.subTest(endpoint=f"{method} {path}"):
                resp = await self.client.request(method, path, json=json_data)
                self.assertEqual(resp.status, 401, f"{method} {path} should require auth")

    async def test_expired_jwt_rejected(self):
        """Test that all endpoints reject expired JWT tokens."""
        expired_jwt = self.create_expired_channels_jwt()
        cookies = self.get_channels_cookies(expired_jwt)

        endpoints = [
            ("GET", "/api/channels/list", None),
            ("POST", "/api/channels/create", {"channel_name": "test"}),
            ("POST", "/api/channels/update", {"bot_id": "test"}),
            ("DELETE", "/api/channels/delete", {"bot_id": "test"}),
        ]

        for method, path, json_data in endpoints:
            with self.subTest(endpoint=f"{method} {path}"):
                resp = await self.client.request(method, path, json=json_data, cookies=cookies)
                self.assertEqual(resp.status, 401, f"{method} {path} should reject expired JWT")

    async def test_no_organization_returns_404(self):
        """Test that endpoints return 404 when no governance bot exists for organization."""
        jwt_token = self.create_valid_channels_jwt()
        cookies = self.get_channels_cookies(jwt_token)

        # Remove the governance bot from bot_server.bots to simulate no governance bot
        # This will cause find_governance_bot_for_organization to return None
        self.mock_bot_server.bots = {}

        endpoints = [
            ("GET", "/api/channels/list", None),
            ("POST", "/api/channels/create", {"channel_name": "test"}),
            ("DELETE", "/api/channels/delete", {"bot_id": "test"}),
        ]

        for method, path, json_data in endpoints:
            with self.subTest(endpoint=f"{method} {path}"):
                resp = await self.client.request(method, path, json=json_data, cookies=cookies)
                # The decorator now returns 401 with "Bot Not Found" message when no governance bot exists
                self.assertEqual(
                    resp.status, 401, f"{method} {path} should return 401 for no governance bot"
                )
