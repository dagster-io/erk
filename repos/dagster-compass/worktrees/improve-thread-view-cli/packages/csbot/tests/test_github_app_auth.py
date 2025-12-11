"""Test GitHub App JWT authentication flow."""

import os
import tempfile
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import jwt
import pytest
from pydantic import SecretStr

from csbot.local_context_store.github.config import PATGithubAuthSource
from csbot.slackbot.slackbot_core import BotGitHubConfig

if TYPE_CHECKING:
    from csbot.local_context_store.github.config import GitHubAppAuthSource


class TestGitHubAppAuthentication:
    """Test GitHub App JWT authentication implementation."""

    def create_test_private_key(self) -> tuple[str, str]:
        """Create a test RSA private key for JWT signing."""
        # Generate a real RSA key pair using cryptography for testing
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Serialize private key to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        # Create a temporary file to store the private key
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(private_key_pem)
            temp_key_path = f.name

        return private_key_pem, temp_key_path

    @pytest.mark.asyncio
    async def test_personal_access_token_auth(self):
        """Test that Personal Access Token authentication works correctly."""
        config = BotGitHubConfig(token=SecretStr("test_pat_token"))

        # Should not be a GitHub App
        assert not config.is_github_app()

        # Should return the token directly
        assert isinstance(config.get_auth_source(), PATGithubAuthSource)
        assert config.get_auth_source().get_token() == "test_pat_token"

    def test_github_app_config_validation(self):
        """Test GitHub App configuration validation."""
        # Should fail with no credentials
        with pytest.raises(
            ValueError, match=r"Either 'token' \(Personal Access Token\) or GitHub App credentials"
        ):
            BotGitHubConfig()

        # Should fail with partial GitHub App config
        with pytest.raises(
            ValueError, match=r"Either 'token' \(Personal Access Token\) or GitHub App credentials"
        ):
            BotGitHubConfig(app_id=12345)

        with pytest.raises(
            ValueError, match=r"Either 'token' \(Personal Access Token\) or GitHub App credentials"
        ):
            BotGitHubConfig(app_id=12345, installation_id=67890)

        # Should fail with both PAT and GitHub App config
        private_key_pem, temp_key_path = self.create_test_private_key()
        try:
            with pytest.raises(
                ValueError, match=r"Cannot specify both 'token' and GitHub App credentials"
            ):
                BotGitHubConfig(
                    token=SecretStr("test_token"),
                    app_id=12345,
                    installation_id=67890,
                    private_key_path=temp_key_path,
                )
        finally:
            os.unlink(temp_key_path)

        # Should succeed with complete GitHub App config
        private_key_pem, temp_key_path = self.create_test_private_key()
        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            assert config.is_github_app()
        finally:
            os.unlink(temp_key_path)

    def test_jwt_generation(self):
        """Test JWT token generation for GitHub App."""
        private_key_pem, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Generate JWT only (not the full token exchange)
            jwt_token = auth_source._generate_github_app_jwt()

            # Verify JWT structure
            assert isinstance(jwt_token, str)
            assert len(jwt_token.split(".")) == 3  # JWT has 3 parts

            # Decode and verify payload (without signature verification for test)
            decoded = jwt.decode(jwt_token, options={"verify_signature": False})

            assert decoded["iss"] == 12345  # App ID
            assert "iat" in decoded  # Issued at
            assert "exp" in decoded  # Expires

            # Verify timing (issued at should be ~1 minute ago, expires in ~10 minutes)
            now = int(time.time())
            assert abs(decoded["iat"] - (now - 60)) <= 5  # Allow 5 second tolerance
            assert abs(decoded["exp"] - (now + 600)) <= 5  # Allow 5 second tolerance

        finally:
            os.unlink(temp_key_path)

    def test_jwt_generation_missing_key_file(self):
        """Test JWT generation with missing private key file."""
        config = BotGitHubConfig(
            app_id=12345, installation_id=67890, private_key_path="/nonexistent/path/key.pem"
        )

        with pytest.raises(FileNotFoundError, match="Private key file not found"):
            config.get_auth_source().get_token()

    def test_jwt_generation_invalid_key_file(self):
        """Test JWT generation with invalid private key file."""
        # Create a temporary file with invalid content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write("invalid key content")
            temp_key_path = f.name

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )

            with pytest.raises(ValueError, match="Failed to generate JWT token"):
                config.get_auth_source().get_token()

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_installation_token_exchange_success(self):
        """Test successful installation token exchange."""
        private_key_pem, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )

            # Mock successful HTTP response
            mock_response_data = {"token": "ghs_test_installation_token"}

            with patch("aiohttp.ClientSession.post") as mock_post:
                # Create mock response context manager
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.json = AsyncMock(return_value=mock_response_data)
                mock_post.return_value.__aenter__.return_value = mock_response

                # Test token exchange
                jwt_token = "test.jwt.token"
                auth_source = cast("GitHubAppAuthSource", config.get_auth_source())
                access_token = await auth_source._get_installation_access_token(jwt_token)

                assert access_token == "ghs_test_installation_token"

                # Verify HTTP request was made correctly
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                expected_url = "https://api.github.com/app/installations/67890/access_tokens"
                assert call_args[0][0] == expected_url

                expected_headers = {
                    "Authorization": "Bearer test.jwt.token",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                assert call_args[1]["headers"] == expected_headers

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_installation_token_exchange_http_error(self):
        """Test installation token exchange with HTTP error."""
        private_key_pem, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )

            with patch("aiohttp.ClientSession.post") as mock_post:
                # Create mock response that raises HTTP error
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock(
                    side_effect=aiohttp.ClientResponseError(request_info=Mock(), history=())
                )
                mock_post.return_value.__aenter__.return_value = mock_response

                with pytest.raises(ValueError, match="Failed to get installation access token"):
                    await cast(
                        "GitHubAppAuthSource", config.get_auth_source()
                    )._get_installation_access_token("test.jwt.token")

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_installation_token_exchange_invalid_response(self):
        """Test installation token exchange with invalid response format."""
        private_key_pem, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )

            with patch("aiohttp.ClientSession.post") as mock_post:
                # Create mock response with missing token
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()
                mock_response.json = AsyncMock(return_value={})  # No token field
                mock_post.return_value.__aenter__.return_value = mock_response

                with pytest.raises(ValueError, match="No access token returned from GitHub API"):
                    await cast(
                        "GitHubAppAuthSource", config.get_auth_source()
                    )._get_installation_access_token("test.jwt.token")

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_end_to_end_github_app_auth(self):
        """Test the complete GitHub App authentication flow."""
        private_key_pem, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )

            # Mock successful installation token response for sync version
            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.return_value = {"token": "ghs_final_access_token"}
                mock_post.return_value = mock_response

                # Get auth token (should handle full flow)
                token = config.get_auth_source().get_token()

                assert token == "ghs_final_access_token"

                # Verify the HTTP call was made
                mock_post.assert_called_once()

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_get_auth_token_with_pat(self):
        """Test get_auth_token with Personal Access Token (should be synchronous)."""
        config = BotGitHubConfig(token=SecretStr("test_pat"))

        # Should return immediately without async operations
        token = config.get_auth_source().get_token()
        assert token == "test_pat"

    def test_github_app_requires_complete_config(self):
        """Test that GitHub App authentication requires all fields."""
        # Missing installation_id should fail at config creation
        with pytest.raises(
            ValueError, match=r"Either 'token' \(Personal Access Token\) or GitHub App credentials"
        ):
            BotGitHubConfig(app_id=12345)

    def test_token_cache_hit(self):
        """Test that cached tokens are returned without making API calls."""
        _, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Manually set a valid cached token (expires in 1 hour)
            now = int(time.time())
            auth_source._cached_token = "ghs_cached_token_12345"
            auth_source._token_expires_at = now + 3300

            with patch("requests.post") as mock_post:
                # Get token should return cached value without API call
                token = auth_source.get_token()
                assert token == "ghs_cached_token_12345"

                # Verify no HTTP requests were made
                mock_post.assert_not_called()

                # Second call should also use cache
                token2 = auth_source.get_token()
                assert token2 == "ghs_cached_token_12345"
                mock_post.assert_not_called()

        finally:
            os.unlink(temp_key_path)

    def test_token_cache_expiry_refresh(self):
        """Test that tokens are refreshed when within 5-minute expiry window."""
        _, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Set cached token that expires in 4 minutes (within refresh window)
            now = int(time.time())
            auth_source._cached_token = "ghs_old_token_12345"
            auth_source._token_expires_at = now + 240  # 4 minutes = 240 seconds

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.return_value = {"token": "ghs_new_refreshed_token"}
                mock_post.return_value = mock_response

                # Should refresh token since it's within 5-minute window
                token = auth_source.get_token()
                assert token == "ghs_new_refreshed_token"

                # Verify API call was made
                mock_post.assert_called_once()

                # Verify cache was updated
                assert auth_source._cached_token == "ghs_new_refreshed_token"
                assert auth_source._token_expires_at == now + 3300  # New expiry

        finally:
            os.unlink(temp_key_path)

    def test_token_cache_miss_no_cached_token(self):
        """Test API call is made when no cached token exists."""
        _, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Ensure no cached token exists
            assert auth_source._cached_token is None
            assert auth_source._token_expires_at is None

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.return_value = {"token": "ghs_fresh_token_12345"}
                mock_post.return_value = mock_response

                # Should make API call since no cache exists
                token = auth_source.get_token()
                assert token == "ghs_fresh_token_12345"

                # Verify API call was made
                mock_post.assert_called_once()

                # Verify cache was populated
                assert auth_source._cached_token == "ghs_fresh_token_12345"
                assert auth_source._token_expires_at is not None

        finally:
            os.unlink(temp_key_path)

    def test_token_cache_expired_token_refresh(self):
        """Test that fully expired tokens trigger refresh."""
        _, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Set expired cached token (expired 1 hour ago)
            now = int(time.time())
            auth_source._cached_token = "ghs_expired_token_12345"
            auth_source._token_expires_at = now - 3300  # Expired 1 hour ago

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.return_value = {"token": "ghs_new_token_after_expiry"}
                mock_post.return_value = mock_response

                # Should refresh token since it's fully expired
                token = auth_source.get_token()
                assert token == "ghs_new_token_after_expiry"

                # Verify API call was made
                mock_post.assert_called_once()

                # Verify cache was updated with new token
                assert auth_source._cached_token == "ghs_new_token_after_expiry"
                assert auth_source._token_expires_at > now  # New expiry in future

        finally:
            os.unlink(temp_key_path)

    @pytest.mark.asyncio
    async def test_sync_async_cache_consistency(self):
        """Test that sync and async methods share the same cache."""
        _, temp_key_path = self.create_test_private_key()

        try:
            config = BotGitHubConfig(
                app_id=12345, installation_id=67890, private_key_path=temp_key_path
            )
            auth_source = cast("GitHubAppAuthSource", config.get_auth_source())

            # Set up mocks for both sync and async HTTP calls
            with (
                patch("requests.post") as mock_sync_post,
                patch("aiohttp.ClientSession.post") as mock_async_post,
            ):
                # Mock sync response
                mock_sync_response = Mock()
                mock_sync_response.raise_for_status = Mock()
                mock_sync_response.json.return_value = {"token": "ghs_sync_token_12345"}
                mock_sync_post.return_value = mock_sync_response

                # Mock async response
                mock_async_response = AsyncMock()
                mock_async_response.raise_for_status = Mock()
                mock_async_response.json = AsyncMock(
                    return_value={"token": "ghs_async_token_12345"}
                )
                mock_async_post.return_value.__aenter__.return_value = mock_async_response

                # First call (sync) should populate cache
                sync_token = auth_source.get_token()
                assert sync_token == "ghs_sync_token_12345"
                mock_sync_post.assert_called_once()

                # Verify cache is populated
                assert auth_source._cached_token == "ghs_sync_token_12345"
                assert auth_source._token_expires_at is not None

                # Second call (async) should use same cache, not make HTTP call
                async_token = await auth_source.get_auth_token()
                assert async_token == "ghs_sync_token_12345"  # Same token from cache
                mock_async_post.assert_not_called()  # No async HTTP call made

                # Clear cache and test async first, then sync
                auth_source._cached_token = None
                auth_source._token_expires_at = None

                # Async call should populate cache
                async_token2 = await auth_source.get_auth_token()
                assert async_token2 == "ghs_async_token_12345"
                mock_async_post.assert_called_once()

                # Sync call should use async-populated cache
                sync_token2 = auth_source.get_token()
                assert sync_token2 == "ghs_async_token_12345"  # Same token from async cache
                assert mock_sync_post.call_count == 1  # No additional sync calls

        finally:
            os.unlink(temp_key_path)
