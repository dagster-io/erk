#!/usr/bin/env python3
"""Detect whether repo uses `main` or `master` as trunk branch.

This command checks the remote (origin) for the existence of trunk branches,
suitable for CI environments where local branches may not be available.

This replaces bash-based detection in GitHub Actions workflows:
```bash
if git ls-remote --heads origin main | grep -q main; then
  echo "trunk_branch=main"
elif git ls-remote --heads origin master | grep -q master; then
  echo "trunk_branch=master"
else
  exit 1
fi
```

Usage:
    erk exec detect-trunk-branch

Output:
    JSON object with success status and detected trunk branch

Exit Codes:
    0: Success (trunk branch detected)
    1: Error (neither main nor master exists on remote)

Examples:
    $ erk exec detect-trunk-branch
    {
      "success": true,
      "trunk_branch": "main"
    }

    $ erk exec detect-trunk-branch  # in repo with master only
    {
      "success": true,
      "trunk_branch": "master"
    }

    $ erk exec detect-trunk-branch  # in repo without main/master
    {
      "success": false,
      "error": "trunk_not_found",
      "message": "Could not detect trunk branch (neither 'main' nor 'master' exists on origin)"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_git, require_repo_root
from erk_shared.git.abc import Git


@dataclass
class DetectedTrunk:
    """Success result with detected trunk branch."""

    success: bool
    trunk_branch: str


@dataclass
class DetectionError:
    """Error result when trunk branch cannot be detected."""

    success: bool
    error: Literal["trunk_not_found", "git_error"]
    message: str


def _detect_trunk_branch_impl(git: Git, repo_root: Path) -> DetectedTrunk | DetectionError:
    """Detect trunk branch by checking remote for main or master.

    Checks origin remote for 'main' first, then 'master'. Returns error
    if neither exists.

    Args:
        git: Git interface for operations
        repo_root: Path to the git repository root

    Returns:
        DetectedTrunk on success, DetectionError if neither branch found
    """
    # Check main first (modern convention), then master (legacy convention)
    for candidate in ["main", "master"]:
        if git.branch_exists_on_remote(repo_root, "origin", candidate):
            return DetectedTrunk(success=True, trunk_branch=candidate)

    # Neither found
    return DetectionError(
        success=False,
        error="trunk_not_found",
        message="Could not detect trunk branch (neither 'main' nor 'master' exists on origin)",
    )


@click.command(name="detect-trunk-branch")
@click.pass_context
def detect_trunk_branch(ctx: click.Context) -> None:
    """Detect whether repo uses main or master as trunk branch.

    Queries the origin remote to check for trunk branch existence.
    Checks for 'main' first, then 'master'. Exits with error if neither exists.
    """
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)

    result = _detect_trunk_branch_impl(git, repo_root)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if detection failed
    if isinstance(result, DetectionError):
        raise SystemExit(1)
