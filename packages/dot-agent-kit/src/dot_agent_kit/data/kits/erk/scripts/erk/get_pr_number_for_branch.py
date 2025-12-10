#!/usr/bin/env python3
"""Get PR number for a given branch name.

This command queries GitHub API to find the PR associated with a branch.
Replaces jq parsing of gh pr view output in workflows.

Usage:
    erk kit exec erk get-pr-number-for-branch --branch "feature-branch"

Output:
    JSON object with success status and PR number

Exit Codes:
    0: Success (PR found)
    1: Error (PR not found or API error)

Examples:
    $ erk kit exec erk get-pr-number-for-branch --branch "my-feature"
    {
      "success": true,
      "pr_number": 1895
    }

    $ erk kit exec erk get-pr-number-for-branch --branch "no-pr-branch"
    {
      "success": false,
      "error": "pr_not_found"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click
from erk_shared.github.abc import GitHub
from erk_shared.github.types import PRNotFound

from dot_agent_kit.context_helpers import require_github, require_repo_root


@dataclass
class LookupSuccess:
    """Success result when PR was found."""

    success: bool
    pr_number: int


@dataclass
class LookupError:
    """Error result when PR lookup fails."""

    success: bool
    error: Literal["pr_not_found"]


def _get_pr_number_for_branch_impl(
    github: GitHub,
    repo_root: Path,
    branch: str,
) -> LookupSuccess | LookupError:
    """Look up PR number for a branch.

    Args:
        github: GitHub interface
        repo_root: Repository root directory
        branch: Branch name to look up

    Returns:
        LookupSuccess with pr_number if found, LookupError otherwise
    """
    pr = github.get_pr_for_branch(repo_root, branch)

    if isinstance(pr, PRNotFound):
        return LookupError(
            success=False,
            error="pr_not_found",
        )

    return LookupSuccess(
        success=True,
        pr_number=pr.number,
    )


@click.command(name="get-pr-number-for-branch")
@click.option("--branch", required=True, help="Branch name to look up PR for")
@click.pass_context
def get_pr_number_for_branch(
    ctx: click.Context,
    branch: str,
) -> None:
    """Get PR number for a branch.

    Queries GitHub API to find the pull request associated with the given
    branch name. Returns the PR number if found.
    """
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    result = _get_pr_number_for_branch_impl(github, repo_root, branch)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, LookupError):
        raise SystemExit(1)
