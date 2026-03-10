"""Detect PR number from the current git branch.

Uses github.get_pr_for_branch() to look up the associated PR for plnd/ branches.
Plan-ref.json is the primary source; this exec script is the fallback when no
.erk/impl-context/ folder exists yet.

Usage:
    erk exec detect-plan-from-branch

Output:
    JSON with detection result:
    {"found": true, "pr_number": 2521, "detection_method": "pr_lookup"}
    {"found": false}

Exit Codes:
    0: Always (caller decides how to handle not-found)

Examples:
    $ erk exec detect-plan-from-branch
    {"found": true, "pr_number": 2521, "detection_method": "pr_lookup"}
"""

import json
from collections.abc import Callable

import click

from erk_shared.context.helpers import require_cwd, require_git, require_github, require_repo_root
from erk_shared.gateway.github.types import PRNotFound


def _detect_plan_from_branch_impl(
    *,
    current_branch: str | None,
    pr_lookup: Callable[[], int | None],
) -> dict[str, object]:
    """Core detection logic, separated for testability.

    Args:
        current_branch: Current branch name, or None if detached HEAD.
        pr_lookup: Callable that returns PR number or None for the current branch.
            Signature: () -> int | None

    Returns:
        Detection result dict with 'found', and optionally 'pr_number' and 'detection_method'.
    """
    if current_branch is None:
        return {"found": False}

    # Look up associated PR for the current branch
    pr_number = pr_lookup()
    if pr_number is not None:
        return {"found": True, "pr_number": pr_number, "detection_method": "pr_lookup"}

    return {"found": False}


@click.command(name="detect-plan-from-branch")
@click.pass_context
def detect_plan_from_branch(ctx: click.Context) -> None:
    """Detect PR number from the current git branch.

    Looks up the associated PR for the current branch.

    Always exits with code 0 - caller decides how to handle not-found.
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    current_branch = git.branch.get_current_branch(cwd)

    def pr_lookup() -> int | None:
        if current_branch is None:
            return None
        pr_result = github.get_pr_for_branch(repo_root, current_branch)
        if isinstance(pr_result, PRNotFound):
            return None
        return pr_result.number

    result = _detect_plan_from_branch_impl(
        current_branch=current_branch,
        pr_lookup=pr_lookup,
    )
    click.echo(json.dumps(result))
