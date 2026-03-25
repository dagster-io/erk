"""Tests for erk_mcp.auth."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from erk_mcp.auth import (
    DEFAULT_GITHUB_OAUTH_SCOPES,
    build_auth_provider_from_env,
    get_authenticated_github_token,
)


class TestBuildAuthProviderFromEnv:
    def test_returns_none_when_github_oauth_env_is_absent(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert build_auth_provider_from_env() is None

    def test_raises_when_github_oauth_env_is_partial(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "ERK_MCP_GITHUB_OAUTH_CLIENT_ID": "client-id",
                "ERK_MCP_PUBLIC_URL": "https://erk.example.com",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET"):
                build_auth_provider_from_env()

    def test_builds_github_provider_with_default_scope(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "ERK_MCP_GITHUB_OAUTH_CLIENT_ID": "client-id",
                "ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET": "client-secret",
                "ERK_MCP_PUBLIC_URL": "https://erk.example.com",
            },
            clear=True,
        ):
            with patch("erk_mcp.auth.GitHubProvider") as mock_provider:
                build_auth_provider_from_env()

        mock_provider.assert_called_once_with(
            client_id="client-id",
            client_secret="client-secret",
            base_url="https://erk.example.com",
            required_scopes=list(DEFAULT_GITHUB_OAUTH_SCOPES),
            require_authorization_consent=False,
        )

    def test_builds_github_provider_with_custom_scopes(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "ERK_MCP_GITHUB_OAUTH_CLIENT_ID": "client-id",
                "ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET": "client-secret",
                "ERK_MCP_PUBLIC_URL": "https://erk.example.com",
                "ERK_MCP_GITHUB_OAUTH_SCOPES": "repo, workflow , read:org",
            },
            clear=True,
        ):
            with patch("erk_mcp.auth.GitHubProvider") as mock_provider:
                build_auth_provider_from_env()

        mock_provider.assert_called_once_with(
            client_id="client-id",
            client_secret="client-secret",
            base_url="https://erk.example.com",
            required_scopes=["repo", "workflow", "read:org"],
            require_authorization_consent=False,
        )


class TestGetAuthenticatedGitHubToken:
    def test_returns_none_when_fastmcp_has_no_access_token(self) -> None:
        with patch("erk_mcp.auth.get_access_token", return_value=None):
            assert get_authenticated_github_token() is None

    def test_returns_none_for_blank_fastmcp_access_token(self) -> None:
        with patch(
            "erk_mcp.auth.get_access_token",
            return_value=SimpleNamespace(token="   "),
        ):
            assert get_authenticated_github_token() is None

    def test_returns_upstream_github_token_from_fastmcp_access_token(self) -> None:
        with patch(
            "erk_mcp.auth.get_access_token",
            return_value=SimpleNamespace(token="upstream-token"),
        ):
            assert get_authenticated_github_token() == "upstream-token"
