#!/usr/bin/env python3
"""Parse GitHub issue reference from URL or plain number.

This command provides robust parsing of GitHub issue references, accepting both
plain issue numbers ("776") and full GitHub URLs
("https://github.com/owner/repo/issues/776").

This replaces bash-based regex parsing in agent markdown with tested Python code.

Usage:
    # Parse plain issue number
    dot-agent run erk parse-issue-reference "776"

    # Parse full GitHub URL
    dot-agent run erk parse-issue-reference "https://github.com/owner/repo/issues/776"

Output:
    JSON object with success status and parsed issue number

Exit Codes:
    0: Success (issue number parsed)
    1: Error (invalid input format)

Examples:
    $ dot-agent run erk parse-issue-reference "776"
    {
      "success": true,
      "issue_number": 776
    }

    $ dot-agent run erk parse-issue-reference "https://github.com/dagster-io/erk/issues/776"
    {
      "success": true,
      "issue_number": 776
    }

    $ dot-agent run erk parse-issue-reference "not-a-number"
    {
      "success": false,
      "error": "invalid_format",
      "message": "Issue reference must be a number or GitHub URL"
    }
"""

import json
import re
from dataclasses import asdict, dataclass
from typing import Literal

import click


@dataclass
class ParsedIssue:
    """Success result with parsed issue number."""

    success: bool
    issue_number: int


@dataclass
class ParseError:
    """Error result when issue reference cannot be parsed."""

    success: bool
    error: Literal["invalid_format", "invalid_number"]
    message: str


def _parse_issue_reference_impl(reference: str) -> ParsedIssue | ParseError:
    """Parse GitHub issue reference from plain number or URL.

    Args:
        reference: Either a plain issue number ("776") or full GitHub URL
                  ("https://github.com/owner/repo/issues/776")

    Returns:
        ParsedIssue on success, ParseError on invalid input
    """
    # Try plain number format first
    if reference.isdigit():
        issue_number = int(reference)
        if issue_number <= 0:
            return ParseError(
                success=False,
                error="invalid_number",
                message=f"Issue number must be positive (got {issue_number})",
            )
        return ParsedIssue(success=True, issue_number=issue_number)

    # Try GitHub URL format
    # Pattern: https://github.com/{owner}/{repo}/issues/{number}
    url_pattern = r"^https?://github\.com/[^/]+/[^/]+/issues/(\d+)(?:[?#].*)?$"
    match = re.match(url_pattern, reference)
    if match:
        issue_number = int(match.group(1))
        if issue_number <= 0:
            return ParseError(
                success=False,
                error="invalid_number",
                message=f"Issue number must be positive (got {issue_number})",
            )
        return ParsedIssue(success=True, issue_number=issue_number)

    # Neither format matched
    return ParseError(
        success=False,
        error="invalid_format",
        message="Issue reference must be a number or GitHub URL (e.g., '776' or 'https://github.com/owner/repo/issues/776')",
    )


@click.command(name="parse-issue-reference")
@click.argument("issue_reference")
def parse_issue_reference(issue_reference: str) -> None:
    """Parse GitHub issue reference from plain number or URL.

    Accepts either a plain issue number (e.g., "776") or a full GitHub URL
    (e.g., "https://github.com/owner/repo/issues/776").
    """
    result = _parse_issue_reference_impl(issue_reference)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if parsing failed
    if isinstance(result, ParseError):
        raise SystemExit(1)
