#!/usr/bin/env python3
"""Rebase onto target branch and resolve conflicts with Claude.

This command handles merge conflicts during CI workflows by:
1. Fetching the target branch (trunk or parent branch for stacked PRs)
2. Checking if the current branch is behind
3. Starting a rebase
4. Using Claude to resolve any conflicts
5. Force pushing after successful rebase
6. Generating an intelligent summary of the rebase operation

Usage:
    erk exec rebase-with-conflict-resolution \
        --target-branch master \
        --branch-name feature-branch \
        --model claude-sonnet-4-5

Output:
    Natural language summary suitable for PR comments.

Exit Codes:
    0: Success (rebase completed and pushed, or already up-to-date)
    1: Error (conflict resolution failed after max attempts)

Examples:
    $ erk exec rebase-with-conflict-resolution --target-branch main --branch-name my-feature
    Rebased `my-feature` onto `main`, resolving 3 commits behind.
    Resolved merge conflicts in 2 files:
    - src/config.py: Merged new logging settings with updated timeout values
    - tests/test_api.py: Combined new test cases with fixture updates

    $ erk exec rebase-with-conflict-resolution \
        --target-branch feature-parent --branch-name my-feature
    Branch `my-feature` is already up-to-date with `feature-parent` (no rebase needed).
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_cwd, require_git
from erk_shared.git.abc import Git


@dataclass(frozen=True)
class RebaseSuccess:
    """Success result for rebase operation."""

    action: Literal["rebased", "already-up-to-date"]
    commits_behind: int
    conflicts_resolved: tuple[str, ...]


@dataclass(frozen=True)
class RebaseError:
    """Error result when rebase fails."""

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


def _generate_summary(
    *,
    branch_name: str,
    target_branch: str,
    commits_behind: int,
    conflicts_resolved: tuple[str, ...],
    model: str,
) -> str:
    """Use Claude to generate an intelligent summary of the rebase.

    Args:
        branch_name: The branch that was rebased
        target_branch: The branch rebased onto
        commits_behind: Number of commits the branch was behind
        conflicts_resolved: Files that had merge conflicts resolved
        model: Claude model to use for summary generation

    Returns:
        Natural language summary suitable for PR comments.
    """
    if not conflicts_resolved:
        conflict_context = "No merge conflicts occurred."
    else:
        files_list = "\n".join(f"- {f}" for f in conflicts_resolved)
        conflict_context = (
            f"Merge conflicts were automatically resolved in these files:\n{files_list}"
        )

    prompt = f"""Generate a brief summary for a GitHub PR comment about a rebase.

Context:
- Branch `{branch_name}` was rebased onto `{target_branch}`
- The branch was {commits_behind} commit(s) behind
- {conflict_context}

Requirements:
- Start with a one-line summary of the rebase
- If there were conflicts, list the files that had conflicts resolved
- Keep the tone professional and concise
- Use markdown formatting (backticks for branch names and file paths)
- Do not include any preamble or explanation - output ONLY the PR comment text"""

    result = subprocess.run(
        [
            "claude",
            "--print",
            "--model",
            model,
            prompt,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip()


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
    *,
    git: Git,
    cwd: Path,
    target_branch: str,
    branch_name: str,
    model: str,
    max_attempts: int,
) -> RebaseSuccess | RebaseError:
    """Rebase onto target branch and resolve conflicts with Claude.

    Args:
        git: Git gateway for repository operations
        cwd: Current working directory (worktree path)
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
            error="fetch-failed",
            message=f"Failed to fetch origin/{target_branch}: {fetch_result.stderr}",
        )

    # Check if behind
    commits_behind = _get_commits_behind(target_branch)
    if commits_behind is None:
        return RebaseError(
            error="fetch-failed",
            message="Failed to determine commits behind target branch",
        )

    if commits_behind == 0:
        return RebaseSuccess(
            action="already-up-to-date",
            commits_behind=0,
            conflicts_resolved=(),
        )

    # Start rebase (may fail with conflicts, which is expected)
    subprocess.run(
        ["git", "rebase", f"origin/{target_branch}"],
        capture_output=True,
        text=True,
        check=False,  # Conflicts expected - we check git.is_rebase_in_progress()
    )

    # Track all files that had conflicts across all resolution attempts
    all_conflicted_files: set[str] = set()

    # Loop while rebase has conflicts
    attempt = 0
    while git.is_rebase_in_progress(cwd) and attempt < max_attempts:
        attempt += 1
        # Capture conflicted files before resolution
        conflicted = git.get_conflicted_files(cwd)
        all_conflicted_files.update(conflicted)
        # Invoke Claude to fix conflicts
        _invoke_claude_for_conflicts(model)

    # Check if rebase completed
    if git.is_rebase_in_progress(cwd):
        # Abort rebase and return error
        subprocess.run(["git", "rebase", "--abort"], capture_output=True, check=False)
        return RebaseError(
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
            error="push-failed",
            message=f"Failed to force push: {push_result.stderr}",
        )

    return RebaseSuccess(
        action="rebased",
        commits_behind=commits_behind,
        conflicts_resolved=tuple(sorted(all_conflicted_files)),
    )


@click.command(name="rebase-with-conflict-resolution")
@click.pass_context
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
    help="Claude model to use for conflict resolution and summary generation",
)
@click.option(
    "--max-attempts",
    default=5,
    type=int,
    help="Maximum number of conflict resolution attempts",
)
def rebase_with_conflict_resolution(
    ctx: click.Context,
    target_branch: str,
    branch_name: str,
    model: str,
    max_attempts: int,
) -> None:
    """Rebase onto target branch and resolve conflicts with Claude.

    This command is designed for CI workflows where push may fail due to
    branch divergence. It fetches the target branch (trunk or parent for
    stacked PRs), rebases onto it, and uses Claude to resolve any merge conflicts.

    Outputs a natural language summary suitable for PR comments.
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)

    result = _rebase_with_conflict_resolution_impl(
        git=git,
        cwd=cwd,
        target_branch=target_branch,
        branch_name=branch_name,
        model=model,
        max_attempts=max_attempts,
    )

    if isinstance(result, RebaseError):
        click.echo(f"Error: {result.message}")
        raise SystemExit(1)

    if result.action == "already-up-to-date":
        click.echo(
            f"Branch `{branch_name}` is already up-to-date with "
            f"`{target_branch}` (no rebase needed)."
        )
    else:
        summary = _generate_summary(
            branch_name=branch_name,
            target_branch=target_branch,
            commits_behind=result.commits_behind,
            conflicts_resolved=result.conflicts_resolved,
            model=model,
        )
        click.echo(summary)
