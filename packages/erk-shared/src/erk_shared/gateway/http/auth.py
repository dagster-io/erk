"""GitHub authentication token retrieval.

This module provides functions to fetch GitHub tokens via the gh CLI,
designed to be called once at startup to avoid repeated subprocess overhead.
"""

from erk_shared.subprocess_utils import run_subprocess_with_context


def fetch_github_token() -> str:
    """Fetch GitHub token via gh CLI.

    This should be called once at startup and cached. The token can then
    be used to create RealHttpClient instances for direct API calls.

    Returns:
        GitHub authentication token

    Raises:
        RuntimeError: If gh auth token fails
        ValueError: If token is empty
    """
    result = run_subprocess_with_context(
        cmd=["gh", "auth", "token", "--hostname", "github.com"],
        operation_context="fetch GitHub token for github.com",
    )
    token = result.stdout.strip()
    if not token:
        msg = "Empty token returned from gh auth for github.com"
        raise ValueError(msg)
    return token


def fetch_github_token_or_none() -> str | None:
    """Fetch GitHub token via gh CLI, returning None if unavailable.

    Use this at startup when GitHub auth is optional (e.g., commands that
    don't require API access). Commands that need a token can fail at
    point-of-use with a clear error.

    Returns:
        GitHub authentication token, or None if gh auth is not configured.
    """
    result = run_subprocess_with_context(
        cmd=["gh", "auth", "token", "--hostname", "github.com"],
        operation_context="fetch GitHub token for github.com",
        check=False,
    )
    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    if not token:
        return None
    return token
