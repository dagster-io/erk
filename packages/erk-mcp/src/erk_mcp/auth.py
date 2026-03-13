"""GitHub OAuth configuration helpers for erk-mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.dependencies import get_access_token

DEFAULT_GITHUB_OAUTH_SCOPES: tuple[str, ...] = ("repo",)


@dataclass(frozen=True, slots=True)
class GitHubOAuthConfig:
    client_id: str
    client_secret: str
    public_url: str
    scopes: tuple[str, ...]


def build_auth_provider_from_env() -> GitHubProvider | None:
    config = _read_github_oauth_config_from_env()
    if config is None:
        return None
    return GitHubProvider(
        client_id=config.client_id,
        client_secret=config.client_secret,
        base_url=config.public_url,
        required_scopes=list(config.scopes),
        require_authorization_consent=False,
    )


def get_authenticated_github_token() -> str | None:
    access_token = get_access_token()
    if access_token is None:
        return None

    token = access_token.token.strip()
    if token == "":
        return None
    return token


def _read_github_oauth_config_from_env() -> GitHubOAuthConfig | None:
    client_id = os.environ.get("ERK_MCP_GITHUB_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET", "").strip()
    public_url = os.environ.get("ERK_MCP_PUBLIC_URL", "").strip()
    scopes = _parse_github_oauth_scopes(os.environ.get("ERK_MCP_GITHUB_OAUTH_SCOPES", "").strip())

    if client_id == "" and client_secret == "" and public_url == "":
        return None

    missing_fields: list[str] = []
    if client_id == "":
        missing_fields.append("ERK_MCP_GITHUB_OAUTH_CLIENT_ID")
    if client_secret == "":
        missing_fields.append("ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET")
    if public_url == "":
        missing_fields.append("ERK_MCP_PUBLIC_URL")

    if missing_fields:
        missing_fields_display = ", ".join(missing_fields)
        raise ValueError(
            f"GitHub OAuth for erk-mcp is partially configured. Missing: {missing_fields_display}."
        )

    return GitHubOAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        public_url=public_url,
        scopes=scopes,
    )


def _parse_github_oauth_scopes(raw_scopes: str) -> tuple[str, ...]:
    if raw_scopes == "":
        return DEFAULT_GITHUB_OAUTH_SCOPES

    scopes = tuple(scope.strip() for scope in raw_scopes.split(",") if scope.strip())
    if len(scopes) == 0:
        return DEFAULT_GITHUB_OAUTH_SCOPES
    return scopes
