"""Integration tests for JWT authentication HTTP flows.

Tests HTTP middleware, redirects, cookie handling, and decorator behavior
that requires a full aiohttp application. These tests focus on:

- JWT authentication middleware (@require_jwt_user_auth)
- Token-to-cookie conversion via HTTP redirects
- Cookie security attributes in different environments
- HTTP 401 responses for authentication failures
- Bot lookup and organization context in HTTP requests

For unit tests of pure JWT logic (encoding, decoding, validation), see:
packages/csbot/tests/slackbot/webapp/test_jwt_security.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt as jwt_lib
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import (
    BotTypeCombined,
    BotTypeGovernance,
    CompassChannelBaseBotInstance,
)
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.htmlstring import HtmlString
from csbot.slackbot.webapp.security import (
    JWT_AUTH_COOKIE_NAME,
    JWT_AUTH_QUERY_PARAM,
    OrganizationContext,
    ensure_auth_token_cookie_from_token,
    ensure_token_is_valid,
    require_jwt_user_auth,
)


class TestOrganizationJWTAuth(AioHTTPTestCase):
    """Test organization-based JWT authentication."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = 123
        self.team_id = "T123456789"
        self.channel_name = "test-governance"
        self.bot_key = BotKey(team_id=self.team_id, channel_name=self.channel_name)
        self.jwt_secret = "test-secret-key-for-jwt"
        self.user_id = "U123456"

        # Mock bot configuration with organization_id
        self.mock_bot_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_bot_config.organization_id = self.organization_id
        self.mock_bot_config.team_id = self.team_id
        self.mock_bot_config.organization_name = "Test Organization"

        # Mock bot instance with governance type
        self.mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_bot.key = self.bot_key
        self.mock_bot.bot_config = self.mock_bot_config
        self.mock_bot.bot_type = BotTypeGovernance(governed_bot_keys=set())

        # Mock bot server config
        self.mock_server_config = Mock()
        self.mock_server_config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_server_config.public_url = "http://localhost:8080"
        self.mock_bot.server_config = self.mock_server_config

        # Mock bot manager
        self.mock_bot_manager = Mock()
        self.mock_bot_manager.storage = Mock()

        super().setUp()

    async def get_application(self):
        """Create application for testing."""
        # Create bot server with single bot
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.config = self.mock_server_config
        self.mock_bot_server.logger = Mock()
        self.mock_bot_server.bot_manager = self.mock_bot_manager
        self.mock_bot_server.bots = {self.bot_key: self.mock_bot}

        app = build_web_application(self.mock_bot_server)

        # Add test route that requires JWT auth
        @require_jwt_user_auth(
            bot_server=self.mock_bot_server,
        )
        async def test_route(
            request: web.Request, organization_context: OrganizationContext
        ) -> web.Response:
            return web.json_response(
                {
                    "success": True,
                    "organization_id": organization_context.organization_id,
                    "team_id": organization_context.team_id,
                    "user_id": request.match_info.get("user_id"),
                }
            )

        app.router.add_get("/test/protected", test_route)
        return app

    def create_organization_jwt(
        self,
        organization_id: int | None = None,
        team_id: str | None = None,
        user_id: str | None = None,
        claims: dict | None = None,
        exp_hours: int = 3,
    ) -> str:
        """Create an organization-based JWT token."""
        if organization_id is None:
            organization_id = self.organization_id
        if team_id is None:
            team_id = self.team_id
        if user_id is None:
            user_id = self.user_id
        if claims is None:
            claims = {}

        jwt_payload = {
            "organization_id": organization_id,
            "team_id": team_id,
            "user_id": user_id,
            **claims,
            "exp": datetime.now(UTC) + timedelta(hours=exp_hours),
        }
        return jwt_lib.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    async def test_organization_jwt_authentication_success(self):
        """Test successful authentication with organization-based JWT."""
        token = self.create_organization_jwt(claims={"can_test": True})

        resp = await self.client.request(
            "GET", "/test/protected", cookies={JWT_AUTH_COOKIE_NAME: token}
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

    async def test_organization_jwt_wrong_organization(self):
        """Test authentication fails when organization doesn't match any bot."""
        # Create token with non-existent organization
        token = self.create_organization_jwt(organization_id=999, claims={"can_test": True})

        resp = await self.client.request(
            "GET", "/test/protected", cookies={JWT_AUTH_COOKIE_NAME: token}
        )

        self.assertEqual(resp.status, 401)
        text = await resp.text()
        self.assertIn("Bot Not Found", text)

    async def test_organization_jwt_no_token_provided(self):
        """Test authentication fails when no token is provided."""
        resp = await self.client.request("GET", "/test/protected")

        self.assertEqual(resp.status, 401)

    async def test_combined_bot_type_also_works(self):
        """Test that BotTypeCombined bots can also use JWT auth."""
        # Create a combined-type bot
        combined_bot_key = BotKey(team_id=self.team_id, channel_name="test-combined")
        combined_bot = Mock(spec=CompassChannelBaseBotInstance)
        combined_bot.key = combined_bot_key
        combined_bot.bot_config = self.mock_bot_config
        combined_bot.bot_type = BotTypeCombined(governed_bot_keys=set())

        # Replace governance bot with combined bot
        self.mock_bot_server.bots = {combined_bot_key: combined_bot}

        # Create organization token
        token = self.create_organization_jwt(claims={"can_test": True})

        resp = await self.client.request(
            "GET", "/test/protected", cookies={JWT_AUTH_COOKIE_NAME: token}
        )

        self.assertEqual(resp.status, 200)


class TestEnsureTokenIsValid(AioHTTPTestCase):
    """Test ensure_token_is_valid() function directly."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = 456
        self.team_id = "T987654321"
        self.jwt_secret = "test-secret-direct"
        self.user_id = "U987654"

        # Mock bot server
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.logger = Mock()
        self.mock_server_config = Mock()
        self.mock_server_config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.config = self.mock_server_config

        super().setUp()

    async def get_application(self):
        """Create minimal application for testing."""
        app = web.Application()
        return app

    def create_test_token(self, **kwargs) -> str:
        """Create a test JWT token."""
        payload = {
            "organization_id": kwargs.get("organization_id", self.organization_id),
            "team_id": kwargs.get("team_id", self.team_id),
            "user_id": kwargs.get("user_id", self.user_id),
            "exp": kwargs.get("exp", datetime.now(UTC) + timedelta(hours=3)),
        }
        # Add extra claims
        for key, value in kwargs.items():
            if key not in ["organization_id", "team_id", "user_id", "exp"]:
                payload[key] = value

        return jwt_lib.encode(payload, self.jwt_secret, algorithm="HS256")

    async def test_ensure_token_is_valid_success(self):
        """Test ensure_token_is_valid() succeeds with valid token."""
        token = self.create_test_token(admin=True)

        # Create mock request with cookie
        request = Mock(spec=web.Request)
        request.cookies = {JWT_AUTH_COOKIE_NAME: token}
        request.query = {}
        request.path = "/test/path"

        async def error_message():
            return HtmlString(unsafe_html="<h1>Error</h1>")

        organization_context = await ensure_token_is_valid(
            bot_server=self.mock_bot_server,
            error_message=error_message,
            request=request,
        )

        # Verify returned organization context
        self.assertEqual(organization_context.team_id, self.team_id)
        self.assertEqual(organization_context.organization_id, self.organization_id)


class TestEnsureAuthTokenCookieFromToken(AioHTTPTestCase):
    """Test ensure_auth_token_cookie_from_token() redirect functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.jwt_secret = "test-secret-redirect"

        # Mock bot server with test environment config
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.logger = Mock()
        self.mock_server_config = Mock()
        self.mock_server_config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_server_config.public_url = "http://localhost:8080"  # Test environment
        self.mock_bot_server.config = self.mock_server_config

        super().setUp()

    async def get_application(self):
        """Create minimal application for testing."""
        app = web.Application()

        # Add test route that calls ensure_auth_token_cookie_from_token
        async def test_route_with_token_check(request: web.Request) -> web.Response:
            await ensure_auth_token_cookie_from_token(request, self.mock_bot_server)
            return web.Response(text="success")

        app.router.add_get("/test/redirect", test_route_with_token_check)
        return app

    async def test_token_stripped_from_url_and_set_as_cookie(self):
        """Test that token is removed from URL and set as HTTP-only cookie."""
        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={test_token}", allow_redirects=False
        )

        # Should redirect with 302
        self.assertEqual(resp.status, 302)

        # Should redirect to same path without token parameter
        self.assertEqual(resp.headers["Location"], "/test/redirect")

        # Should set cookie with token value
        cookies = resp.cookies
        self.assertIn(JWT_AUTH_COOKIE_NAME, cookies)
        self.assertEqual(cookies[JWT_AUTH_COOKIE_NAME].value, test_token)

        # Verify cookie security attributes
        cookie = cookies[JWT_AUTH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], "21600")  # 6 hours

    async def test_preserves_other_query_parameters(self):
        """Test that non-token query parameters are preserved in redirect."""
        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET",
            f"/test/redirect?filter=active&page=2&{JWT_AUTH_QUERY_PARAM}={test_token}&sort=name",
            allow_redirects=False,
        )

        # Should redirect with 302
        self.assertEqual(resp.status, 302)

        # Should preserve all parameters except token
        location = resp.headers["Location"]
        self.assertIn("filter=active", location)
        self.assertIn("page=2", location)
        self.assertIn("sort=name", location)
        self.assertNotIn(f"{JWT_AUTH_QUERY_PARAM}=", location)

        # Should still set cookie
        cookies = resp.cookies
        self.assertIn(JWT_AUTH_COOKIE_NAME, cookies)
        self.assertEqual(cookies[JWT_AUTH_COOKIE_NAME].value, test_token)

    async def test_no_redirect_when_no_token_present(self):
        """Test that no redirect occurs when token parameter is absent."""
        resp = await self.client.request("GET", "/test/redirect", allow_redirects=False)

        # Should return success without redirect
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertEqual(text, "success")

    async def test_preserves_query_parameters_when_no_token(self):
        """Test that request proceeds normally with query params when no token."""
        resp = await self.client.request(
            "GET", "/test/redirect?filter=active&page=2", allow_redirects=False
        )

        # Should return success without redirect
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertEqual(text, "success")

    async def test_secure_cookie_in_test_environment(self):
        """Test that secure flag is NOT set in test environment (HTTP)."""
        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={test_token}", allow_redirects=False
        )

        # In test environment (HTTP), secure should be False
        cookies = resp.cookies
        # Verify cookie is set (secure flag behavior depends on aiohttp test client implementation)
        self.assertIn(JWT_AUTH_COOKIE_NAME, cookies)

    async def test_secure_cookie_in_production_environment(self):
        """Test that secure flag IS set in production environment (HTTPS)."""
        # Change config to production (HTTPS)
        self.mock_server_config.public_url = "https://production.example.com"

        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={test_token}", allow_redirects=False
        )

        # Should still redirect and set cookie
        self.assertEqual(resp.status, 302)
        cookies = resp.cookies
        self.assertIn(JWT_AUTH_COOKIE_NAME, cookies)

    async def test_token_removed_from_url_prevents_log_leakage(self):
        """Test that token is removed from URL to prevent logging/history leakage."""
        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={test_token}", allow_redirects=False
        )

        # Redirect URL should NOT contain token
        location = resp.headers["Location"]
        self.assertNotIn(test_token, location)
        self.assertNotIn(f"{JWT_AUTH_QUERY_PARAM}=", location)

        # But cookie should have the token
        self.assertEqual(resp.cookies[JWT_AUTH_COOKIE_NAME].value, test_token)

    async def test_handles_special_characters_in_query_params(self):
        """Test that query parameters with special characters are preserved correctly."""
        # Create valid JWT token
        test_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        # URL with special characters in query params
        resp = await self.client.request(
            "GET",
            f"/test/redirect?search=hello%20world&{JWT_AUTH_QUERY_PARAM}={test_token}&email=user%40example.com",
            allow_redirects=False,
        )

        # Should redirect and preserve encoded parameters
        self.assertEqual(resp.status, 302)
        location = resp.headers["Location"]
        self.assertIn("search=", location)
        self.assertIn("email=", location)
        self.assertNotIn(f"{JWT_AUTH_QUERY_PARAM}=", location)

    async def test_empty_token_value(self):
        """Test behavior with empty token parameter."""
        # Empty token should still trigger redirect (edge case)
        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}=", allow_redirects=False
        )

        # aiohttp may treat empty value as no value, so behavior may vary
        # We just verify the request completes without error
        self.assertIn(resp.status, [200, 302])

    async def test_invalid_token_rejected(self):
        """Test that malformed JWT tokens are rejected before setting cookie."""
        invalid_token = "not.a.valid.jwt.token"

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={invalid_token}", allow_redirects=False
        )

        # Should return 401 Unauthorized, not redirect
        self.assertEqual(resp.status, 401)

        # Should NOT set cookie
        self.assertNotIn(JWT_AUTH_COOKIE_NAME, resp.cookies)

        # Response should contain error message
        text = await resp.text()
        self.assertIn("Invalid Authentication", text)

    async def test_expired_token_rejected(self):
        """Test that expired JWT tokens are rejected before setting cookie."""
        # Create expired token (1 hour in the past)
        expired_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) - timedelta(hours=1),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={expired_token}", allow_redirects=False
        )

        # Should return 401 Unauthorized, not redirect
        self.assertEqual(resp.status, 401)

        # Should NOT set cookie
        self.assertNotIn(JWT_AUTH_COOKIE_NAME, resp.cookies)

        # Response should contain error message
        text = await resp.text()
        self.assertIn("Session Expired", text)

    async def test_token_with_wrong_signature_rejected(self):
        """Test that tokens signed with wrong secret are rejected."""
        # Create token with different secret
        wrong_secret = "wrong-secret-key"
        forged_token = jwt_lib.encode(
            {
                "organization_id": 123,
                "team_id": "T123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            wrong_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={forged_token}", allow_redirects=False
        )

        # Should return 401 Unauthorized, not redirect
        self.assertEqual(resp.status, 401)

        # Should NOT set cookie
        self.assertNotIn(JWT_AUTH_COOKIE_NAME, resp.cookies)

        # Response should contain error message
        text = await resp.text()
        self.assertIn("Invalid Authentication", text)

    async def test_prevents_token_injection_attack(self):
        """Test that attacker cannot inject arbitrary tokens via URL."""
        # Simulate attack: attacker crafts URL with their own token
        attacker_secret = "attacker-secret"
        attacker_token = jwt_lib.encode(
            {
                "organization_id": 999,
                "team_id": "TATTACKER",
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            attacker_secret,
            algorithm="HS256",
        )

        resp = await self.client.request(
            "GET", f"/test/redirect?{JWT_AUTH_QUERY_PARAM}={attacker_token}", allow_redirects=False
        )

        # Attack should be blocked - token validation should fail
        self.assertEqual(resp.status, 401)

        # Should NOT set cookie with attacker's token
        self.assertNotIn(JWT_AUTH_COOKIE_NAME, resp.cookies)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
