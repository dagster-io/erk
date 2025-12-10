#!/usr/bin/env python3
"""Create an empty commit and push to trigger CI workflows.

This command creates an empty commit and pushes it to trigger CI pipelines.
Replaces the pattern: git commit --allow-empty -m "message" && git push

Usage:
    erk kit exec erk trigger-ci-push --branch "feature-branch" --message "Trigger CI"

Output:
    JSON object with success status

Exit Codes:
    0: Success (push completed)
    1: Error (git command failed)

Examples:
    $ erk kit exec erk trigger-ci-push --branch "feature" --message "Trigger CI workflows"
    {
      "success": true,
      "sha": "abc1234"
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
class TriggerSuccess:
    """Success result when trigger commit was pushed."""

    success: bool
    sha: str


@dataclass
class TriggerError:
    """Error result when trigger fails."""

    success: bool
    error: Literal["commit_failed", "push_failed"]
    message: str


def _trigger_ci_push_impl(
    git: Git,
    cwd: Path,
    branch: str,
    message: str,
) -> TriggerSuccess | TriggerError:
    """Create empty commit and push to trigger CI.

    Args:
        git: Git interface for operations
        cwd: Current working directory
        branch: Branch name to push to
        message: Commit message for the empty commit

    Returns:
        TriggerSuccess on success, TriggerError on failure
    """
    # Create empty commit (the Git ABC commit method uses --allow-empty)
    git.commit(cwd, message)

    # Get the commit SHA
    sha = git.get_branch_head(cwd, "HEAD")
    if sha is None:
        sha = "unknown"

    # Push to remote
    git.push_to_remote(cwd, "origin", branch)

    return TriggerSuccess(
        success=True,
        sha=sha[:7] if len(sha) >= 7 else sha,
    )


@click.command(name="trigger-ci-push")
@click.option("--branch", required=True, help="Branch name to push to")
@click.option("--message", required=True, help="Commit message for empty commit")
@click.pass_context
def trigger_ci_push(ctx: click.Context, branch: str, message: str) -> None:
    """Create empty commit and push to trigger CI workflows.

    Creates an empty commit with the provided message and pushes it to
    the specified branch on origin to trigger CI pipelines.
    """
    git = require_git(ctx)
    cwd = require_cwd(ctx)

    result = _trigger_ci_push_impl(git, cwd, branch, message)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, TriggerError):
        raise SystemExit(1)
