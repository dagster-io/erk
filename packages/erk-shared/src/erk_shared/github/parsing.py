"""Parsing utilities for GitHub operations."""

import json
import re
from pathlib import Path
from typing import Any

from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation, PRInfo
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


PASSING_CHECK_RUN_STATES = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL"})
PASSING_STATUS_CONTEXT_STATES = frozenset({"SUCCESS"})


def extract_owner_repo_from_github_url(url: str) -> tuple[str, str] | None:
    """Extract owner and repo from any GitHub URL.

    Works with PR URLs, issue URLs, and other GitHub URLs that follow
    the pattern: https://github.com/owner/repo/...

    Args:
        url: GitHub URL (e.g., "https://github.com/owner/repo/issues/123")

    Returns:
        Tuple of (owner, repo) or None if URL doesn't match expected pattern

    Example:
        >>> extract_owner_repo_from_github_url("https://github.com/dagster-io/erk/issues/23")
        ("dagster-io", "erk")
        >>> extract_owner_repo_from_github_url("https://github.com/dagster-io/erk/pull/45")
        ("dagster-io", "erk")
    """
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)(?:/|$)", url)
    if match:
        return (match.group(1), match.group(2))
    return None


def parse_git_remote_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a git remote URL.

    Supports both HTTPS and SSH formats for GitHub URLs:
        - HTTPS: https://github.com/owner/repo.git or https://github.com/owner/repo
        - SSH: git@github.com:owner/repo.git

    Args:
        url: Git remote URL

    Returns:
        Tuple of (owner, repo)

    Raises:
        ValueError: If URL is not a valid GitHub URL

    Example:
        >>> parse_git_remote_url("https://github.com/dagster-io/erk.git")
        ("dagster-io", "erk")
        >>> parse_git_remote_url("git@github.com:dagster-io/erk.git")
        ("dagster-io", "erk")
    """
    # Handle HTTPS format: https://github.com/owner/repo.git
    https_match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if https_match:
        return (https_match.group(1), https_match.group(2))

    # Handle SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if ssh_match:
        return (ssh_match.group(1), ssh_match.group(2))

    raise ValueError(f"Not a valid GitHub URL: {url}")


def github_repo_location_from_url(root: Path, github_url: str) -> GitHubRepoLocation | None:
    """Create GitHubRepoLocation from a GitHub URL.

    Extracts owner/repo from the URL and combines with local root path.
    Returns None if URL doesn't match expected GitHub pattern.

    Args:
        root: Local repository root path
        github_url: GitHub URL (e.g., "https://github.com/owner/repo/issues/123")

    Returns:
        GitHubRepoLocation or None if URL doesn't match expected pattern
    """
    owner_repo = extract_owner_repo_from_github_url(github_url)
    if owner_repo is None:
        return None
    return GitHubRepoLocation(root=root, repo_id=GitHubRepoId(owner_repo[0], owner_repo[1]))


def parse_aggregated_check_counts(
    check_run_counts: list[dict[str, Any]],
    status_context_counts: list[dict[str, Any]],
    total_count: int,
) -> tuple[int, int]:
    """Parse aggregated check counts from GitHub GraphQL response.

    Returns (passing, total) tuple.

    Passing criteria:
        - CheckRun: SUCCESS, SKIPPED, NEUTRAL
        - StatusContext: SUCCESS
    """
    passing = 0

    for item in check_run_counts:
        state = item.get("state", "")
        count = item.get("count", 0)
        if state in PASSING_CHECK_RUN_STATES:
            passing += count

    for item in status_context_counts:
        state = item.get("state", "")
        count = item.get("count", 0)
        if state in PASSING_STATUS_CONTEXT_STATES:
            passing += count

    return (passing, total_count)


def parse_issue_number_from_url(url: str) -> int | None:
    """Extract issue number from GitHub issue URL.

    Args:
        url: GitHub issue URL (e.g., "https://github.com/owner/repo/issues/123")

    Returns:
        Issue number as int, or None if URL doesn't match expected pattern.
        Also handles URLs with query strings or fragments like
        "https://github.com/owner/repo/issues/789#issuecomment-123"

    Example:
        >>> parse_issue_number_from_url("https://github.com/owner/repo/issues/123")
        123
        >>> parse_issue_number_from_url("https://github.com/owner/repo/issues/789#issuecomment-123")
        789
    """
    match = re.match(r"https://github\.com/[^/]+/[^/]+/issues/(\d+)", url)
    if match:
        return int(match.group(1))
    return None


def parse_pr_number_from_url(url: str) -> int | None:
    """Extract PR number from GitHub PR URL.

    Args:
        url: GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")

    Returns:
        PR number as int, or None if URL doesn't match expected pattern.
        Also handles URLs with query strings or fragments like
        "https://github.com/owner/repo/pull/789#issuecomment-123"

    Example:
        >>> parse_pr_number_from_url("https://github.com/owner/repo/pull/123")
        123
        >>> parse_pr_number_from_url("https://github.com/owner/repo/pull/789#issuecomment-123")
        789
    """
    match = re.match(r"https://github\.com/[^/]+/[^/]+/pull/(\d+)", url)
    if match:
        return int(match.group(1))
    return None


def construct_workflow_run_url(owner: str, repo: str, run_id: int | str) -> str:
    """Construct GitHub Actions workflow run URL.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run ID (int or string)

    Returns:
        Workflow run URL

    Example:
        >>> construct_workflow_run_url("dagster-io", "erk", 1234567890)
        "https://github.com/dagster-io/erk/actions/runs/1234567890"
    """
    return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"


def construct_pr_url(owner: str, repo: str, pr_number: int) -> str:
    """Construct GitHub PR URL.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number

    Returns:
        PR URL

    Example:
        >>> construct_pr_url("dagster-io", "erk", 123)
        "https://github.com/dagster-io/erk/pull/123"
    """
    return f"https://github.com/{owner}/{repo}/pull/{pr_number}"


def construct_issue_url(owner: str, repo: str, issue_number: int) -> str:
    """Construct GitHub issue URL.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number

    Returns:
        Issue URL

    Example:
        >>> construct_issue_url("dagster-io", "erk", 456)
        "https://github.com/dagster-io/erk/issues/456"
    """
    return f"https://github.com/{owner}/{repo}/issues/{issue_number}"


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
