"""Token resolution for Anthropic Admin API access."""

import json
import os
import platform
import subprocess

from erk.cli.ensure import UserFacingCliError


def resolve_tokens(*, tokens: tuple[str, ...]) -> list[str]:
    """Resolve API tokens from CLI args, environment, or keychain.

    Priority order:
    1. Explicit --token flags (if provided)
    2. ANTHROPIC_ADMIN_KEY environment variable
    3. ANTHROPIC_API_KEY environment variable
    4. macOS Keychain (Claude Code credentials)

    Args:
        tokens: Tuple of tokens from --token CLI option.

    Returns:
        List of resolved API tokens.

    Raises:
        UserFacingCliError: If no tokens can be resolved.
    """
    if tokens:
        return list(tokens)

    admin_key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if admin_key:
        return [admin_key]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return [api_key]

    keychain_token = _read_keychain_token()
    if keychain_token is not None:
        return [keychain_token]

    raise UserFacingCliError(
        "No API token found. Provide --token, set ANTHROPIC_ADMIN_KEY or "
        "ANTHROPIC_API_KEY, or ensure Claude Code credentials exist in the "
        "macOS Keychain."
    )


def _read_keychain_token() -> str | None:
    """Read Claude Code OAuth token from macOS Keychain.

    Returns:
        The OAuth access token, or None if not available.
    """
    if platform.system() != "Darwin":
        return None

    result = subprocess.run(
        ["security", "find-generic-password", "-s", "Claude Code-credentials", "-g"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    # Parse the password from stderr (security outputs password to stderr)
    for line in result.stderr.splitlines():
        if line.startswith("password:"):
            raw = line[len("password:") :].strip()
            # Remove surrounding quotes if present
            if raw.startswith('"') and raw.endswith('"'):
                raw = raw[1:-1]
            # Handle hex-encoded passwords
            if raw.startswith("0x"):
                try:
                    raw = bytes.fromhex(raw[2:].replace(" ", "")).decode("utf-8")
                except (ValueError, UnicodeDecodeError):
                    return None
            try:
                creds = json.loads(raw)
            except json.JSONDecodeError:
                return None
            oauth = creds.get("claudeAiOauth")
            if oauth is None:
                return None
            token = oauth.get("accessToken")
            if isinstance(token, str) and token:
                return token
            return None

    return None
