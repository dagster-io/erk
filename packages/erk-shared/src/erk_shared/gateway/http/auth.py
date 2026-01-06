"""GitHub authentication token retrieval.

This module provides functions to fetch GitHub tokens via the gh CLI,
designed to be called once at startup to avoid repeated subprocess overhead.
"""

from erk_shared.subprocess_utils import run_subprocess_with_context


def fetch_github_token(hostname: str = "github.com") -> str:
    """Fetch GitHub token via gh CLI.

    This should be called once at startup and cached. The token can then
    be used to create RealHttpClient instances for direct API calls.

    Args:
        hostname: GitHub hostname (default: "github.com")

    Returns:
        GitHub authentication token

    Raises:
        RuntimeError: If gh auth token fails
        ValueError: If token is empty
    """
    result = run_subprocess_with_context(
        cmd=["gh", "auth", "token", "--hostname", hostname],
        operation_context=f"fetch GitHub token for {hostname}",
    )
    token = result.stdout.strip()
    if not token:
        msg = f"Empty token returned from gh auth for {hostname}"
        raise ValueError(msg)
    return token
