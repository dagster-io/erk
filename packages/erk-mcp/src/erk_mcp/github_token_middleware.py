"""Middleware that reads Bearer token from Authorization header into a ContextVar."""

from __future__ import annotations

from fastmcp.server.http import _current_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

from erk_mcp.request_context import reset_request_github_token, set_request_github_token


class GitHubTokenMiddleware(Middleware):
    """Extract Bearer token from Authorization header and set per-request GitHub token ContextVar.

    No validation is performed — Compass is trusted to send the correct token.
    Falls back to process-level GH_TOKEN when no Authorization header is present.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        request = _current_http_request.get()
        if request is not None:
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                user_token = auth[len("Bearer "):]
                tok = set_request_github_token(user_token)
                try:
                    return await call_next(context)
                finally:
                    reset_request_github_token(tok)
        return await call_next(context)
