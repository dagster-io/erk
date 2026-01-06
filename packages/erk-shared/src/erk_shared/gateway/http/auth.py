"""GitHub authentication token retrieval.

This module provides functions to fetch GitHub tokens via the gh CLI,
designed to be called once at startup to avoid repeated subprocess overhead.
"""

import subprocess


def fetch_github_token(hostname: str = "github.com") -> str:
    """Fetch GitHub token via gh CLI.

    This should be called once at startup and cached. The token can then
    be used to create RealHttpClient instances for direct API calls.

    Args:
        hostname: GitHub hostname (default: "github.com")

    Returns:
        GitHub authentication token

    Raises:
        subprocess.CalledProcessError: If gh auth token fails
        ValueError: If token is empty
    """
    result = subprocess.run(
        ["gh", "auth", "token", "--hostname", hostname],
        capture_output=True,
        text=True,
        check=True,
    )
    token = result.stdout.strip()
    if not token:
        msg = f"Empty token returned from gh auth for {hostname}"
        raise ValueError(msg)
    return token
