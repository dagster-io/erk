"""Parsing utilities for plan commands."""

from urllib.parse import urlparse

import click


def parse_issue_number(identifier: str) -> int:
    """Parse issue number from identifier string.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub issue URL)

    Returns:
        Issue number as int

    Raises:
        click.ClickException: If identifier cannot be parsed as an issue number
    """
    if identifier.isdigit():
        return int(identifier)

    # Try to parse from GitHub URL
    parsed = urlparse(identifier)
    if parsed.scheme and parsed.hostname:
        if parsed.hostname == "github.com" and parsed.path:
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 2 and parts[-2] == "issues":
                last_part = parts[-1]
                if last_part.isdigit():
                    return int(last_part)
        raise click.ClickException(
            f"Invalid URL format: {identifier!r}. "
            "Expected format: https://github.com/OWNER/REPO/issues/NUMBER"
        )

    raise click.ClickException(
        f"Invalid plan identifier: {identifier!r}. "
        "Expected an issue number (e.g., '42') or GitHub issue URL."
    )
