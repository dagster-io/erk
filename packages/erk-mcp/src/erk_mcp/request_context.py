"""Per-request ContextVar for GitHub token injection."""

from __future__ import annotations

from contextvars import ContextVar, Token

_github_token_for_request: ContextVar[str | None] = ContextVar(
    "_github_token_for_request", default=None
)


def set_request_github_token(token: str) -> Token[str | None]:
    return _github_token_for_request.set(token)


def get_request_github_token() -> str | None:
    return _github_token_for_request.get()


def reset_request_github_token(token: Token[str | None]) -> None:
    _github_token_for_request.reset(token)
