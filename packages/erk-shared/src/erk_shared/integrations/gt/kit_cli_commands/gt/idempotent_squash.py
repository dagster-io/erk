#!/usr/bin/env python3
"""Idempotent squash - squash commits only if needed.

Squashes all commits on the current branch into one, but only if there
are 2 or more commits. If already a single commit, returns success with
no operation performed.

Usage:
    dot-agent run gt idempotent-squash

Output:
    JSON object with success status and action taken:

    Success (squashed):
    {
      "success": true,
      "action": "squashed",
      "commit_count": 3,
      "message": "Squashed 3 commits into 1."
    }

    Success (no-op):
    {
      "success": true,
      "action": "already_single_commit",
      "commit_count": 1,
      "message": "Already a single commit, no squash needed."
    }

    Error:
    {
      "success": false,
      "error": "no_commits",
      "message": "No commits found ahead of main."
    }

Exit Codes:
    0: Success (either squashed or already single commit)
    1: Error (no commits, squash failed, etc.)

Error Types:
    - no_commits: No commits found ahead of trunk
    - squash_conflict: Merge conflicts during squash
    - squash_failed: Generic squash failure
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import RealGtKit


@dataclass
class SquashSuccess:
    """Success result from idempotent squash."""

    success: Literal[True]
    action: Literal["squashed", "already_single_commit"]
    commit_count: int
    message: str


@dataclass
class SquashError:
    """Error result from idempotent squash."""

    success: Literal[False]
    error: Literal["no_commits", "squash_conflict", "squash_failed"]
    message: str


def execute_squash(ops: GtKit | None = None) -> SquashSuccess | SquashError:
    """Execute idempotent squash.

    Args:
        ops: Optional GtKit for dependency injection. If None, uses RealGtKit.

    Returns:
        SquashSuccess if squash succeeded or was unnecessary,
        SquashError if squash failed.
    """
    if ops is None:
        ops = RealGtKit()

    cwd = Path.cwd()
    repo_root = ops.git().get_repository_root(cwd)

    # Step 1: Get trunk branch
    trunk = ops.git().detect_trunk_branch(repo_root)

    # Step 2: Count commits
    commit_count = ops.git().count_commits_ahead(cwd, trunk)
    if commit_count == 0:
        return SquashError(
            success=False,
            error="no_commits",
            message=f"No commits found ahead of {trunk}.",
        )

    # Step 3: If already single commit, return success with no-op
    if commit_count == 1:
        return SquashSuccess(
            success=True,
            action="already_single_commit",
            commit_count=1,
            message="Already a single commit, no squash needed.",
        )

    # Step 4: Squash commits
    try:
        ops.main_graphite().squash_branch(repo_root, quiet=True)
    except subprocess.CalledProcessError as e:
        combined = (e.stdout if hasattr(e, "stdout") else "") + (
            e.stderr if hasattr(e, "stderr") else ""
        )
        if "conflict" in combined.lower():
            return SquashError(
                success=False,
                error="squash_conflict",
                message="Merge conflicts detected during squash.",
            )
        stderr = e.stderr if hasattr(e, "stderr") else ""
        return SquashError(
            success=False,
            error="squash_failed",
            message=f"Failed to squash: {stderr.strip()}",
        )

    return SquashSuccess(
        success=True,
        action="squashed",
        commit_count=commit_count,
        message=f"Squashed {commit_count} commits into 1.",
    )


@click.command(name="idempotent-squash")
def idempotent_squash() -> None:
    """Squash commits on current branch (idempotent - skips if already single commit)."""
    result = execute_squash()
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, SquashError):
        raise SystemExit(1)
