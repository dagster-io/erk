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

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_claude_executor, require_cwd, require_git
from erk_shared.core.claude_executor import ClaudeExecutor
from erk_shared.gateway.git.abc import Git


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


def _build_summary_prompt(
    *,
    branch_name: str,
    target_branch: str,
    commits_behind: int,
    conflicts_resolved: tuple[str, ...],
) -> str:
    """Build the prompt for generating a rebase summary.

    Args:
        branch_name: The branch that was rebased
        target_branch: The branch rebased onto
        commits_behind: Number of commits the branch was behind
        conflicts_resolved: Files that had merge conflicts resolved

    Returns:
        Prompt string for Claude.
    """
    if not conflicts_resolved:
        conflict_context = "No merge conflicts occurred."
    else:
        files_list = "\n".join(f"- {f}" for f in conflicts_resolved)
        conflict_context = (
            f"Merge conflicts were automatically resolved in these files:\n{files_list}"
        )

    return f"""Generate a brief summary for a GitHub PR comment about a rebase.

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


def _generate_summary(
    *,
    claude_executor: ClaudeExecutor,
    cwd: Path,
    branch_name: str,
    target_branch: str,
    commits_behind: int,
    conflicts_resolved: tuple[str, ...],
    model: str,
) -> str:
    """Use Claude to generate an intelligent summary of the rebase.

    Args:
        claude_executor: Claude CLI executor gateway
        cwd: Working directory for Claude execution
        branch_name: The branch that was rebased
        target_branch: The branch rebased onto
        commits_behind: Number of commits the branch was behind
        conflicts_resolved: Files that had merge conflicts resolved
        model: Claude model to use for summary generation

    Returns:
        Natural language summary suitable for PR comments.
    """
    prompt = _build_summary_prompt(
        branch_name=branch_name,
        target_branch=target_branch,
        commits_behind=commits_behind,
        conflicts_resolved=conflicts_resolved,
    )

    result = claude_executor.execute_prompt(
        prompt,
        model=model,
        tools=None,
        cwd=cwd,
        system_prompt=None,
    )

    return result.output.strip()


CONFLICT_RESOLUTION_PROMPT = (
    "Fix all merge conflicts in this repository. "
    "For each conflicted file, read it, resolve the conflict markers appropriately, "
    "and save the file. After fixing all conflicts, stage the resolved files with "
    "'git add' and then run 'git rebase --continue' to continue the rebase."
)


def _invoke_claude_for_conflicts(
    *,
    claude_executor: ClaudeExecutor,
    cwd: Path,
    model: str,
) -> bool:
    """Invoke Claude to fix merge conflicts.

    Args:
        claude_executor: Claude CLI executor gateway
        cwd: Working directory for Claude execution
        model: Claude model to use

    Returns:
        True if Claude invocation succeeded (exit code 0).
    """
    exit_code = claude_executor.execute_prompt_passthrough(
        CONFLICT_RESOLUTION_PROMPT,
        model=model,
        tools=None,
        cwd=cwd,
        dangerous=True,
    )
    return exit_code == 0


def _rebase_with_conflict_resolution_impl(
    *,
    git: Git,
    claude_executor: ClaudeExecutor,
    cwd: Path,
    target_branch: str,
    branch_name: str,
    model: str,
    max_attempts: int,
) -> RebaseSuccess | RebaseError:
    """Rebase onto target branch and resolve conflicts with Claude.

    Args:
        git: Git gateway for repository operations
        claude_executor: Claude CLI executor gateway
        cwd: Current working directory (worktree path)
        target_branch: Branch to rebase onto (trunk or parent branch for stacked PRs)
        branch_name: Current branch name for force push
        model: Claude model to use for conflict resolution
        max_attempts: Maximum number of conflict resolution attempts

    Returns:
        RebaseSuccess on success, RebaseError on failure
    """
    # Fetch target branch
    try:
        git.fetch_branch(cwd, "origin", target_branch)
    except Exception as e:
        return RebaseError(
            error="fetch-failed",
            message=f"Failed to fetch origin/{target_branch}: {e}",
        )

    # Check if behind using ahead_behind
    try:
        _ahead, behind = git.branch.get_ahead_behind(cwd, branch_name)
    except Exception:
        return RebaseError(
            error="fetch-failed",
            message="Failed to determine commits behind target branch",
        )

    if behind == 0:
        return RebaseSuccess(
            action="already-up-to-date",
            commits_behind=0,
            conflicts_resolved=(),
        )

    # Start rebase (may fail with conflicts, which is expected)
    rebase_result = git.rebase_onto(cwd, f"origin/{target_branch}")

    # Track all files that had conflicts across all resolution attempts
    all_conflicted_files: set[str] = set()

    # If rebase had conflicts, add them to our tracking
    if not rebase_result.success:
        all_conflicted_files.update(rebase_result.conflict_files)

    # Loop while rebase has conflicts
    attempt = 0
    while git.is_rebase_in_progress(cwd) and attempt < max_attempts:
        attempt += 1
        # Capture conflicted files before resolution
        conflicted = git.get_conflicted_files(cwd)
        all_conflicted_files.update(conflicted)
        # Invoke Claude to fix conflicts
        _invoke_claude_for_conflicts(
            claude_executor=claude_executor,
            cwd=cwd,
            model=model,
        )

    # Check if rebase completed
    if git.is_rebase_in_progress(cwd):
        # Abort rebase and return error
        git.rebase_abort(cwd)
        return RebaseError(
            error="rebase-failed",
            message=f"Failed to resolve conflicts after {max_attempts} attempts",
        )

    # Force push after successful rebase
    try:
        git.push_to_remote(cwd, "origin", branch_name, force=True, set_upstream=False)
    except Exception as e:
        return RebaseError(
            error="push-failed",
            message=f"Failed to force push: {e}",
        )

    return RebaseSuccess(
        action="rebased",
        commits_behind=behind,
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
    claude_executor = require_claude_executor(ctx)

    result = _rebase_with_conflict_resolution_impl(
        git=git,
        claude_executor=claude_executor,
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
            claude_executor=claude_executor,
            cwd=cwd,
            branch_name=branch_name,
            target_branch=target_branch,
            commits_behind=result.commits_behind,
            conflicts_resolved=result.conflicts_resolved,
            model=model,
        )
        click.echo(summary)
