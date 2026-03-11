"""Tests for GitHubTokenMiddleware Bearer token extraction."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from erk_mcp.github_token_middleware import GitHubTokenMiddleware
from erk_mcp.request_context import get_request_github_token


class TestGitHubTokenMiddleware:
    """Tests for GitHubTokenMiddleware.on_call_tool()."""

    def _make_context(self) -> MagicMock:
        return MagicMock()

    def _make_request(self, authorization: str | None = None) -> MagicMock:
        request = MagicMock()
        headers = {}
        if authorization is not None:
            headers["authorization"] = authorization
        request.headers.get = lambda key, default="": headers.get(key, default)
        return request

    def test_sets_context_var_from_bearer_token(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        request = self._make_request("Bearer my-github-token")
        captured_token: list[str | None] = []

        async def call_next(ctx):
            captured_token.append(get_request_github_token())
            return "result"

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = request
            result = asyncio.run(middleware.on_call_tool(context, call_next))

        assert result == "result"
        assert captured_token == ["my-github-token"]

    def test_resets_context_var_after_call(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        request = self._make_request("Bearer token-abc")

        async def call_next(ctx):
            return "ok"

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = request
            asyncio.run(middleware.on_call_tool(context, call_next))

        assert get_request_github_token() is None

    def test_resets_context_var_on_exception(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        request = self._make_request("Bearer token-abc")

        async def call_next(ctx):
            raise RuntimeError("boom")

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = request
            with pytest.raises(RuntimeError, match="boom"):
                asyncio.run(middleware.on_call_tool(context, call_next))

        assert get_request_github_token() is None

    def test_no_token_set_when_no_authorization_header(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        request = self._make_request()
        captured_token: list[str | None] = []

        async def call_next(ctx):
            captured_token.append(get_request_github_token())
            return "result"

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = request
            asyncio.run(middleware.on_call_tool(context, call_next))

        assert captured_token == [None]

    def test_no_token_set_when_non_bearer_auth(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        request = self._make_request("Basic dXNlcjpwYXNz")
        captured_token: list[str | None] = []

        async def call_next(ctx):
            captured_token.append(get_request_github_token())
            return "result"

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = request
            asyncio.run(middleware.on_call_tool(context, call_next))

        assert captured_token == [None]

    def test_fallback_when_no_http_request(self) -> None:
        middleware = GitHubTokenMiddleware()
        context = self._make_context()
        captured_token: list[str | None] = []

        async def call_next(ctx):
            captured_token.append(get_request_github_token())
            return "result"

        with patch("erk_mcp.github_token_middleware._current_http_request") as mock_var:
            mock_var.get.return_value = None
            asyncio.run(middleware.on_call_tool(context, call_next))

        assert captured_token == [None]
