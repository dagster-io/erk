#!/usr/bin/env python3
"""Rebase onto target branch and resolve conflicts with Claude.

This command handles merge conflicts during CI workflows by:
1. Fetching the target branch (trunk or parent branch for stacked PRs)
2. Checking if the current branch is behind
3. Starting a rebase
4. Using Claude to resolve any conflicts
5. Force pushing after successful rebase

Usage:
    erk exec rebase-with-conflict-resolution \
        --target-branch master \
        --branch-name feature-branch \
        --model claude-sonnet-4-5

Output:
    JSON object with success status

Exit Codes:
    0: Success (rebase completed and pushed, or already up-to-date)
    1: Error (conflict resolution failed after max attempts)

Examples:
    $ erk exec rebase-with-conflict-resolution --target-branch main --branch-name my-feature
    {
      "success": true,
      "action": "rebased",
      "commits_behind": 3
    }

    $ erk exec rebase-with-conflict-resolution \
        --target-branch feature-parent --branch-name my-feature
    {
      "success": true,
      "action": "already-up-to-date",
      "commits_behind": 0
    }
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click


@dataclass(frozen=True)
class RebaseSuccess:
    """Success result for rebase operation."""

    success: bool
    action: Literal["rebased", "already-up-to-date"]
    commits_behind: int


@dataclass(frozen=True)
class RebaseError:
    """Error result when rebase fails."""

    success: bool
    error: Literal["fetch-failed", "rebase-failed", "push-failed"]
    message: str


def _get_commits_behind(target_branch: str) -> int | None:
    """Get number of commits behind target branch.

    Returns:
        Number of commits behind, or None if command fails.
    """
    result = subprocess.run(
        ["git", "rev-list", "--count", f"HEAD..origin/{target_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    count_str = result.stdout.strip()
    if not count_str.isdigit():
        return None
    return int(count_str)


def _is_rebase_in_progress() -> bool:
    """Check if a rebase is currently in progress."""
    git_dir = Path(".git")
    return (git_dir / "rebase-merge").is_dir() or (git_dir / "rebase-apply").is_dir()


def _invoke_claude_for_conflicts(model: str) -> bool:
    """Invoke Claude to fix merge conflicts.

    Returns:
        True if Claude invocation succeeded (exit code 0).
    """
    prompt = (
        "Fix all merge conflicts in this repository. "
        "For each conflicted file, read it, resolve the conflict markers appropriately, "
        "and save the file. After fixing all conflicts, stage the resolved files with "
        "'git add' and then run 'git rebase --continue' to continue the rebase."
    )
    result = subprocess.run(
        [
            "claude",
            "--print",
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--verbose",
            prompt,
        ],
        capture_output=False,  # Let output stream to stdout/stderr
        check=False,  # We check returncode explicitly below
    )
    return result.returncode == 0


def _rebase_with_conflict_resolution_impl(
    target_branch: str,
    branch_name: str,
    model: str,
    max_attempts: int,
) -> RebaseSuccess | RebaseError:
    """Rebase onto target branch and resolve conflicts with Claude.

    Args:
        target_branch: Branch to rebase onto (trunk or parent branch for stacked PRs)
        branch_name: Current branch name for force push
        model: Claude model to use for conflict resolution
        max_attempts: Maximum number of conflict resolution attempts

    Returns:
        RebaseSuccess on success, RebaseError on failure
    """
    # Fetch target branch
    fetch_result = subprocess.run(
        ["git", "fetch", "origin", target_branch],
        capture_output=True,
        text=True,
        check=False,  # We check returncode explicitly below
    )
    if fetch_result.returncode != 0:
        return RebaseError(
            success=False,
            error="fetch-failed",
            message=f"Failed to fetch origin/{target_branch}: {fetch_result.stderr}",
        )

    # Check if behind
    commits_behind = _get_commits_behind(target_branch)
    if commits_behind is None:
        return RebaseError(
            success=False,
            error="fetch-failed",
            message="Failed to determine commits behind target branch",
        )

    if commits_behind == 0:
        return RebaseSuccess(
            success=True,
            action="already-up-to-date",
            commits_behind=0,
        )

    # Start rebase (may fail with conflicts, which is expected)
    subprocess.run(
        ["git", "rebase", f"origin/{target_branch}"],
        capture_output=True,
        text=True,
        check=False,  # Conflicts expected - we check _is_rebase_in_progress()
    )

    # Loop while rebase has conflicts
    attempt = 0
    while _is_rebase_in_progress() and attempt < max_attempts:
        attempt += 1
        # Invoke Claude to fix conflicts
        _invoke_claude_for_conflicts(model)

    # Check if rebase completed
    if _is_rebase_in_progress():
        # Abort rebase and return error
        subprocess.run(["git", "rebase", "--abort"], capture_output=True, check=False)
        return RebaseError(
            success=False,
            error="rebase-failed",
            message=f"Failed to resolve conflicts after {max_attempts} attempts",
        )

    # Force push after successful rebase
    push_result = subprocess.run(
        ["git", "push", "-f", "origin", branch_name],
        capture_output=True,
        text=True,
        check=False,  # We check returncode explicitly below
    )
    if push_result.returncode != 0:
        return RebaseError(
            success=False,
            error="push-failed",
            message=f"Failed to force push: {push_result.stderr}",
        )

    return RebaseSuccess(
        success=True,
        action="rebased",
        commits_behind=commits_behind,
    )


@click.command(name="rebase-with-conflict-resolution")
@click.option(
    "--target-branch",
    required=True,
    help="Branch to rebase onto (trunk or parent branch for stacked PRs)",
)
@click.option(
    "--branch-name",
    required=True,
    help="Current branch name for force push",
)
@click.option(
    "--model",
    default="claude-sonnet-4-5",
    help="Claude model to use for conflict resolution",
)
@click.option(
    "--max-attempts",
    default=5,
    type=int,
    help="Maximum number of conflict resolution attempts",
)
def rebase_with_conflict_resolution(
    target_branch: str,
    branch_name: str,
    model: str,
    max_attempts: int,
) -> None:
    """Rebase onto target branch and resolve conflicts with Claude.

    This command is designed for CI workflows where push may fail due to
    branch divergence. It fetches the target branch (trunk or parent for
    stacked PRs), rebases onto it, and uses Claude to resolve any merge conflicts.
    """
    result = _rebase_with_conflict_resolution_impl(
        target_branch=target_branch,
        branch_name=branch_name,
        model=model,
        max_attempts=max_attempts,
    )

    click.echo(json.dumps(asdict(result), indent=2))

    if isinstance(result, RebaseError):
        raise SystemExit(1)
