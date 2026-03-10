"""Pure helper functions for TUI background operations."""

from __future__ import annotations

import re

from erk.tui.operations.types import OperationResult

_LEARN_PLAN_RE = re.compile(r"Created learn plan #(\d+)")


def last_output_line(result: OperationResult) -> str:
    """Return the last non-empty output line, or 'Unknown error'."""
    return next((ln for ln in reversed(result.output_lines) if ln), "Unknown error")


def extract_learn_plan_number(result: OperationResult) -> int | None:
    """Extract learn plan number from land-execute output, if present."""
    for line in result.output_lines:
        match = _LEARN_PLAN_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def build_github_url(pr_url: str, resource_type: str, number: int) -> str:
    """Build a GitHub URL for a PR or issue from an existing plan URL.

    Args:
        pr_url: Base plan URL (e.g., https://github.com/owner/repo/pull/123)
        resource_type: Either "pull" or "issues"
        number: The PR or issue number

    Returns:
        Full URL (e.g., https://github.com/owner/repo/pull/456)
    """
    # Try /pull/ first (new plan-as-PR format), fall back to /issues/ (legacy)
    if "/pull/" in pr_url:
        base_url = pr_url.rsplit("/pull/", 1)[0]
    else:
        base_url = pr_url.rsplit("/issues/", 1)[0]
    return f"{base_url}/{resource_type}/{number}"
