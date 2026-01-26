"""CLI-level wrappers for GitHub URL parsing with error handling.

This module provides CLI-friendly wrappers around the shared parsing functions
in erk_shared.gateway.github.parsing. These wrappers handle user input (not just URLs)
and raise SystemExit(1) with appropriate error messages for invalid input.

Two-layer architecture:
- erk_shared.gateway.github.parsing: Pure parsing functions, return None on failure (LBYL-friendly)
- src/erk/cli/github_parsing.py: CLI wrappers that raise SystemExit(1)
"""

import click

from erk_shared.gateway.github.parsing import (
    parse_issue_number_from_url,
    parse_pr_number_from_url,
)
from erk_shared.output.output import user_output


def parse_issue_identifier(identifier: str) -> int:
    """Parse issue number from plain number, P-prefixed ID, or GitHub issue URL.

    This is a CLI-level function that handles user input.

    Args:
        identifier: Plain number ("42"), P-prefixed ("P42"), or GitHub issue URL

    Returns:
        Issue number as int

    Raises:
        SystemExit: If identifier cannot be parsed

    Examples:
        >>> parse_issue_identifier("42")
        42
        >>> parse_issue_identifier("P123")
        123
        >>> parse_issue_identifier("p456")
        456
        >>> parse_issue_identifier("https://github.com/owner/repo/issues/123")
        123
    """
    # P-prefixed identifier (e.g., "P123" or "p123")
    if identifier.upper().startswith("P") and identifier[1:].isdigit():
        return int(identifier[1:])

    # Plain number (handles leading zeros like "0042" -> 42)
    if identifier.isdigit():
        return int(identifier)

    # GitHub URL
    issue_number = parse_issue_number_from_url(identifier)
    if issue_number is not None:
        return issue_number

    user_output(
        click.style("Error: ", fg="red")
        + f"Invalid issue number or URL: {identifier}\n\n"
        + "Expected formats:\n"
        + "  • Plain number: 123\n"
        + "  • P-prefixed: P123\n"
        + "  • GitHub URL: https://github.com/owner/repo/issues/456"
    )
    raise SystemExit(1)


def parse_pr_identifier(identifier: str) -> int:
    """Parse PR number from plain number or GitHub PR URL.

    This is a CLI-level function that handles user input.

    Args:
        identifier: Plain number ("42") or GitHub PR URL

    Returns:
        PR number as int

    Raises:
        SystemExit: If identifier cannot be parsed

    Examples:
        >>> parse_pr_identifier("42")
        42
        >>> parse_pr_identifier("https://github.com/owner/repo/pull/123")
        123
    """
    # Plain number (handles leading zeros like "0042" -> 42)
    if identifier.isdigit():
        return int(identifier)

    # Try strict github.com /pull/ URL only
    pr_number = parse_pr_number_from_url(identifier)
    if pr_number is not None:
        return pr_number

    user_output(
        click.style("Error: ", fg="red")
        + f"Invalid PR number or URL: {identifier}\n\n"
        + "Expected formats:\n"
        + "  • Plain number: 123\n"
        + "  • GitHub URL: https://github.com/owner/repo/pull/456"
    )
    raise SystemExit(1)
