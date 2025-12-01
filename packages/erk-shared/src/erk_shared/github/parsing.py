"""Parsing utilities for GitHub operations."""

import json
import re
from pathlib import Path

from erk_shared.github.types import PRInfo, PullRequestInfo
from erk_shared.subprocess_utils import run_subprocess_with_context


def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    """Execute a gh CLI command and return stdout.

    Timing is handled by run_subprocess_with_context.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for command execution

    Returns:
        stdout from the command

    Raises:
        RuntimeError: If command fails with enriched error context
        FileNotFoundError: If gh is not installed
    """
    result = run_subprocess_with_context(
        cmd,
        operation_context="execute gh command",
        cwd=cwd,
    )
    return result.stdout


def parse_github_pr_list(json_str: str, include_checks: bool) -> dict[str, PullRequestInfo]:
    """Parse gh pr list JSON output into PullRequestInfo objects.

    Args:
        json_str: JSON string from gh pr list command
        include_checks: Whether check status is included in JSON

    Returns:
        Mapping of branch name to PullRequestInfo
    """
    prs_data = json.loads(json_str)
    prs = {}

    for pr in prs_data:
        branch = pr["headRefName"]

        # Only determine check status if we fetched it
        checks_passing = None
        if include_checks and "statusCheckRollup" in pr:
            checks_passing = _determine_checks_status(pr["statusCheckRollup"])

        # Parse owner and repo from GitHub URL
        url = pr["url"]
        parsed = _parse_github_pr_url(url)
        if parsed is None:
            # Skip PRs with malformed URLs (shouldn't happen in practice)
            continue
        owner, repo = parsed

        prs[branch] = PullRequestInfo(
            number=pr["number"],
            state=pr["state"],
            url=url,
            is_draft=pr["isDraft"],
            title=pr.get("title"),
            checks_passing=checks_passing,
            owner=owner,
            repo=repo,
        )

    return prs


def parse_github_pr_status(json_str: str) -> PRInfo:
    """Parse gh pr status JSON output.

    Args:
        json_str: JSON string from gh pr list command for a specific branch

    Returns:
        PRInfo with state, pr_number, and title
        - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
        - pr_number: PR number or None if no PR exists
        - title: PR title or None if no PR exists
    """
    prs_data = json.loads(json_str)

    # If no PR exists for this branch
    if not prs_data:
        return PRInfo("NONE", None, None)

    # Take the first (and should be only) PR
    pr = prs_data[0]
    return PRInfo(pr["state"], pr["number"], pr["title"])


def _determine_checks_status(check_rollup: list[dict]) -> bool | None:
    """Determine overall CI checks status.

    Returns:
        None if no checks configured
        True if all checks passed (SUCCESS, SKIPPED, or NEUTRAL)
        False if any check failed or is pending
    """
    if not check_rollup:
        return None

    # GitHub check conclusions that should be treated as passing
    passing_conclusions = {"SUCCESS", "SKIPPED", "NEUTRAL"}

    for check in check_rollup:
        status = check.get("status")
        conclusion = check.get("conclusion")

        # If any check is not completed, consider it failing
        if status != "COMPLETED":
            return False

        # If any completed check didn't pass, consider it failing
        if conclusion not in passing_conclusions:
            return False

    return True


def _parse_github_pr_url(url: str) -> tuple[str, str] | None:
    """Parse owner and repo from GitHub PR URL.

    Args:
        url: GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")

    Returns:
        Tuple of (owner, repo) or None if URL doesn't match expected pattern

    Example:
        >>> _parse_github_pr_url("https://github.com/dagster-io/erk/pull/23")
        ("dagster-io", "erk")
    """
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/\d+", url)
    if match:
        return (match.group(1), match.group(2))
    return None


def parse_gh_auth_status_output(output: str) -> tuple[bool, str | None, str | None]:
    """Parse gh auth status output to extract authentication info.

    Handles both old and new gh CLI output formats:
    - Old format: "✓ Logged in to github.com as USERNAME"
    - New format: "✓ Logged in to github.com account USERNAME (keyring)"

    Args:
        output: Combined stdout and stderr from `gh auth status`

    Returns:
        Tuple of (is_authenticated, username, hostname)
        - is_authenticated: True if user is logged in
        - username: GitHub username or None if not parseable
        - hostname: GitHub hostname (e.g., "github.com") or None if not parseable
    """
    username: str | None = None
    hostname: str | None = None

    for line in output.split("\n"):
        if "Logged in to" not in line:
            continue

        # Try new format first: "Logged in to github.com account USERNAME (keyring)"
        if " account " in line:
            parts = line.split(" account ")
            if len(parts) >= 2:
                # Extract username (first word before any parentheses)
                username_part = parts[1].strip().split()[0]
                username = username_part.rstrip("(")
                # Extract hostname from "Logged in to github.com"
                logged_in_part = parts[0]
                if "Logged in to" in logged_in_part:
                    host_part = logged_in_part.split("Logged in to")[-1].strip()
                    hostname = host_part if host_part else None
        # Fall back to old format: "Logged in to github.com as USERNAME"
        elif " as " in line:
            parts = line.split(" as ")
            if len(parts) >= 2:
                username = parts[1].strip().split()[0] if parts[1].strip() else None
                # Extract hostname from "Logged in to github.com"
                logged_in_part = parts[0]
                if "Logged in to" in logged_in_part:
                    host_part = logged_in_part.split("Logged in to")[-1].strip()
                    hostname = host_part if host_part else None
        break

    # If we found username, authentication is successful
    if username:
        return (True, username, hostname)

    # Fallback: if checkmark present and no parse, still consider authenticated
    if "✓" in output:
        return (True, None, None)

    return (False, None, None)
