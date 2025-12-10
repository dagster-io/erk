#!/usr/bin/env python3
"""Commit and push changes if the working directory is dirty.

This command checks for uncommitted changes and commits/pushes them if present.
Eliminates duplicated git status + commit + push logic in workflows.

Usage:
    erk kit exec erk commit-and-push-if-dirty --branch "feature-branch" --message "Update files"

Output:
    JSON object with success status and whether commit was made

Exit Codes:
    0: Success (either committed or no changes to commit)
    1: Error (git command failed)

Examples:
    $ erk kit exec erk commit-and-push-if-dirty --branch "feature" --message "Update plan"
    {
      "success": true,
      "committed": true,
      "sha": "abc1234"
    }

    $ erk kit exec erk commit-and-push-if-dirty --branch "feature" --message "Update plan"
    {
      "success": true,
      "committed": false,
      "message": "No changes to commit"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click
from erk_shared.git.abc import Git

from dot_agent_kit.context_helpers import require_cwd, require_git


@dataclass
class CommitSuccess:
    """Success result when changes were committed."""

    success: bool
    committed: bool
    sha: str


@dataclass
class NoChanges:
    """Success result when no changes to commit."""

    success: bool
    committed: bool
    message: str


@dataclass
class CommitError:
    """Error result when commit/push fails."""

    success: bool
    error: Literal["git_error", "push_failed"]
    message: str


def _commit_and_push_if_dirty_impl(
    git: Git,
    cwd: Path,
    branch: str,
    message: str,
) -> CommitSuccess | NoChanges | CommitError:
    """Commit and push if there are uncommitted changes.

    Args:
        git: Git interface for operations
        cwd: Current working directory
        branch: Branch name to push to
        message: Commit message

    Returns:
        CommitSuccess if committed, NoChanges if clean, CommitError on failure
    """
    # Check if there are any changes
    if not git.has_uncommitted_changes(cwd):
        return NoChanges(
            success=True,
            committed=False,
            message="No changes to commit",
        )

    # Stage all changes
    git.add_all(cwd)

    # Commit
    git.commit(cwd, message)

    # Get the commit SHA
    sha = git.get_branch_head(cwd, "HEAD")
    if sha is None:
        sha = "unknown"

    # Push to remote
    git.push_to_remote(cwd, "origin", branch)

    return CommitSuccess(
        success=True,
        committed=True,
        sha=sha[:7] if len(sha) >= 7 else sha,
    )


@click.command(name="commit-and-push-if-dirty")
@click.option("--branch", required=True, help="Branch name to push to")
@click.option("--message", required=True, help="Commit message")
@click.pass_context
def commit_and_push_if_dirty(ctx: click.Context, branch: str, message: str) -> None:
    """Commit and push changes if working directory is dirty.

    Checks for uncommitted changes using git status. If changes exist,
    stages all changes, commits with the provided message, and pushes
    to the specified branch on origin.
    """
    git = require_git(ctx)
    cwd = require_cwd(ctx)

    result = _commit_and_push_if_dirty_impl(git, cwd, branch, message)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, CommitError):
        raise SystemExit(1)
