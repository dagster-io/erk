"""Tests for RenderSecretStore retry behavior."""

from unittest.mock import AsyncMock, patch

import pytest

from csbot.slackbot.slackbot_secrets import RenderSecretStore


@pytest.mark.asyncio
async def test_render_secret_store_retries_on_429():
    """Test that RenderSecretStore retries multiple times on 429 rate limit responses."""
    service_id = "test-service-id"
    api_key = "test-api-key"
    org_id = 123
    secret_key = "test_secret.txt"

    # Mock encrypted content response
    with patch("csbot.slackbot.slackbot_secrets.decrypt_string") as mock_decrypt:
        mock_decrypt.return_value = "decrypted-secret-value"

        # Create mock responses: first two are 429, third is success
        mock_response_429_1 = AsyncMock()
        mock_response_429_1.status_code = 429

        mock_response_429_2 = AsyncMock()
        mock_response_429_2.status_code = 429

        mock_response_success = AsyncMock()
        mock_response_success.status_code = 200
        mock_response_success.json = lambda: {"content": "encrypted-content"}

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Configure mock to return 429 twice, then success
        mock_client.get.side_effect = [
            mock_response_429_1,
            mock_response_429_2,
            mock_response_success,
        ]

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("backoff._async._next_wait", return_value=0),
        ):
            secret_store = RenderSecretStore(service_id, api_key)
            result = await secret_store.get_secret_contents(org_id, secret_key)

            # Verify the secret was retrieved after retries
            assert result == "decrypted-secret-value"

            # Verify httpx client was called 3 times (2 failures + 1 success)
            assert mock_client.get.call_count == 3

            # Verify all calls were to the correct URL with correct headers
            expected_url = f"https://api.render.com/v1/services/{service_id}/secret-files/org_{org_id}__test_secret_txt"
            expected_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            for call in mock_client.get.call_args_list:
                assert call.args[0] == expected_url
                assert call.kwargs["headers"] == expected_headers
